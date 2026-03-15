"""
Graph related API routing
Adopt project context mechanism to persist state on the server side
"""

import os
import time
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get the logger
logger = get_logger('mirofish.api')

# Simple in-memory cache for graph data to avoid repeated DB queries on polls
_graph_data_cache: dict = {}  # {graph_id: {"data": ..., "ts": time.time()}}
_GRAPH_CACHE_TTL = 60  # seconds


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project management interface ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
Get project details
"""
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
list all items
"""
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
Delete project
"""
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Project does not exist or deletion failed: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
Reset project status (used to rebuild the graph)
"""
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404
    
    #Reset to the state where the body has been generated
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"Project has been reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Interface 1: Upload files and generate the body ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
Interface 1: Upload files, analyze and generate ontology definitions

Request method: multipart/form-data

Parameters:
files: Uploaded files (PDF/MD/TXT), multiple
simulation_requirement: simulation requirement description (required)
project_name: project name (optional)
additional_context: additional description (optional)

Return:
{
"success": true,
"data": {
"project_id": "proj_xxxx",
"ontology": {
"entity_types": [...],
"edge_types": [...],
"analysis_summary": "..."
},
"files": [...],
"total_text_length": 12345
}
}
"""
    try:
        logger.info("=== Start generating ontology definition ===")
        
        # Get parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        
        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Simulation requirements: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Please provide a description of simulation requirements (simulation_requirement)"
            }), 400
        
        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload at least one document file"
            }), 400
        
        #Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Create project: {project.project_id}")
        
        # Save file and extract text
        document_texts = []
        all_text = ""
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Save the file to the project directory
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                #Extract text
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "No documents were successfully processed, please check the file format"
            }), 400
        
        # Save the extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction completed, total {len(all_text)} characters")
        
        # Generation body
        logger.info("Calling LLM to generate an ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )
        
        # Save the ontology to the project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generation completed: {entity_count} entity types, {edge_count} relationship types")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation completed === Project ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface 2: Build graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
Interface 2: Build a graph based on project_id

Request (JSON):
{
"project_id": "proj_xxxx", // required, from interface 1
"graph_name": "graph name", // optional
"chunk_size": 500, // optional, default 500
"chunk_overlap": 50 // Optional, default 50
}

Return:
{
"success": true,
"data": {
"project_id": "proj_xxxx",
"task_id": "task_xxxx",
"message": "The graph construction task has been started"
}
}
"""
    try:
        logger.info("=== Start building the graph ===")
        
        # Parse the request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request parameter: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400
        
        # Get items
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {project_id}"
            }), 404
        
        # Check project status
        force = data.get('force', False)  # Force rebuild
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "The project has not generated ontology yet, please call /ontology/generate first"
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "The graph is under construction, please do not submit again. If you need to force reconstruction, please add force: true",
                "task_id": project.graph_build_task_id
            }), 400
        
        # If forced to rebuild, reset status
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = data.get('graph_name', project.name or 'MiroFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get the extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "Extracted text content not found"
            }), 400
        
        # Get the ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "Ontology definition not found"
            }), 400
        
        # Create an asynchronous task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Create graph construction task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Start background task
        def build_task():
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info(f"[{task_id}] starts building the graph...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="Initialize the graph construction service..."
                )
                
                #Create a graph construction service
                builder = GraphBuilderService()
                
                # Chunking
                task_manager.update_task(
                    task_id,
                    message="Text chunking...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                #Create graph
                task_manager.update_task(
                    task_id,
                    message="Create graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # Update the graph_id of the project
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # Set the ontology
                task_manager.update_task(
                    task_id,
                    message="Set ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (progress_callback signature is (msg, progress_ratio))
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"Start adding {total_chunks} text chunks...",
                    progress=15
                )
                
                builder.add_text_batches(
                    graph_id,
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )

                # Get map data
                task_manager.update_task(
                    task_id,
                    message="Get map data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # Update project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] graph construction completed: graph_id={graph_id}, node={node_count}, edge={edge_count}")
                
                # Finish
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph construction completed",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                #Update project status to failed
                build_logger.error(f"[{task_id}] graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=traceback.format_exc()
                )
        
        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "The graph construction task has been started, please check the progress through /task/{task_id}"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Task query interface ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
Query task status
"""
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"Task does not exist: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
List all tasks
"""
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== Atlas data interface ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
Get graph data (nodes and edges). Uses in-memory cache to avoid excessive DB queries.
"""
    try:
        # Check cache first
        cached = _graph_data_cache.get(graph_id)
        now = time.time()
        if cached and (now - cached["ts"]) < _GRAPH_CACHE_TTL:
            return jsonify({
                "success": True,
                "data": cached["data"]
            })

        builder = GraphBuilderService()
        graph_data = builder.get_graph_data(graph_id)

        # Store in cache
        _graph_data_cache[graph_id] = {"data": graph_data, "ts": now}

        return jsonify({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        # If we have stale cached data, serve it instead of erroring
        cached = _graph_data_cache.get(graph_id)
        if cached:
            logger.warning(f"DB error for graph {graph_id}, serving cached data: {str(e)[:100]}")
            return jsonify({
                "success": True,
                "data": cached["data"]
            })

        logger.error(f"Failed to fetch graph data for {graph_id}: {str(e)[:200]}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
Delete graph
"""
    try:
        builder = GraphBuilderService()
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
