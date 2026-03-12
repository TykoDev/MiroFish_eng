import os
import json
import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from ..config import Config


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0              # 总进度百分比 0-100
    message: str = ""              # 状态消息
    result: Optional[Dict] = None  # 任务结果
    error: Optional[str] = None    # 错误信息
    metadata: Dict = field(default_factory=dict)  # 额外元数据
    progress_detail: Dict = field(default_factory=dict)  # 详细进度信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class TaskManager:
    """
    任务管理器
    线程安全的任务状态管理，支持文件持久化
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
                    cls._instance._persistence_file = os.path.join(Config.UPLOAD_FOLDER, 'tasks.json')
                    cls._instance._load_from_disk()
        return cls._instance
    
    def _save_to_disk(self):
        """保存任务到磁盘 (原子写入)"""
        try:
            with self._task_lock:
                data = {tid: task.to_dict() for tid, task in self._tasks.items()}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self._persistence_file), exist_ok=True)
            
            # 使用临时文件进行原子写入，防止进程崩溃导致文件损坏
            temp_file = self._persistence_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子替换
            os.replace(temp_file, self._persistence_file)
            
        except Exception as e:
            # 延迟导入以避免循环依赖
            from ..utils.logger import get_logger
            logger = get_logger('mirofish.task')
            logger.error(f"保存任务持久化文件失败: {str(e)}")

    def _load_from_disk(self):
        """从磁盘加载任务"""
        if not os.path.exists(self._persistence_file):
            return
            
        try:
            with open(self._persistence_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self._task_lock:
                for tid, t_dict in data.items():
                    try:
                        self._tasks[tid] = Task(
                            task_id=t_dict['task_id'],
                            task_type=t_dict['task_type'],
                            status=TaskStatus(t_dict['status']),
                            created_at=datetime.fromisoformat(t_dict['created_at']),
                            updated_at=datetime.fromisoformat(t_dict['updated_at']),
                            progress=t_dict.get('progress', 0),
                            message=t_dict.get('message', ''),
                            result=t_dict.get('result'),
                            error=t_dict.get('error'),
                            metadata=t_dict.get('metadata', {}),
                            progress_detail=t_dict.get('progress_detail', {})
                        )
                    except Exception as te:
                        # 记录单条记录加载失败
                        import traceback
                        print(f"加载任务记录 {tid} 失败: {str(te)}")
        except Exception as e:
            from ..utils.logger import get_logger
            logger = get_logger('mirofish.task')
            logger.error(f"加载任务持久化文件失败: {str(e)}")

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        """
        创建新任务
        
        Args:
            task_type: 任务类型
            metadata: 额外元数据
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )
        
        with self._task_lock:
            self._tasks[task_id] = task
        
        self._save_to_disk()
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._task_lock:
            return self._tasks.get(task_id)
    
    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度
            message: 消息
            result: 结果
            error: 错误信息
            progress_detail: 详细进度信息
        """
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.updated_at = datetime.now()
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if message is not None:
                    task.message = message
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
                if progress_detail is not None:
                    task.progress_detail = progress_detail
        
        self._save_to_disk()
    
    def complete_task(self, task_id: str, result: Dict):
        """标记任务完成"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="任务完成",
            result=result
        )
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="任务失败",
            error=error
        )
    
    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """列出任务"""
        with self._task_lock:
            tasks = list(self._tasks.values())
            if task_type:
                tasks = [t for t in tasks if t.task_type == task_type]
            return [t.to_dict() for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._task_lock:
            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            for tid in old_ids:
                del self._tasks[tid]
        
        if old_ids:
            self._save_to_disk()

