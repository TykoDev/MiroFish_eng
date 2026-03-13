# Refactor Tracking Status

## Root Files
- [x] `./README-EN.md`
- [x] `./docker-compose.yml`
- [x] `./package.json`
- [x] `./README.md`
- [x] `./test_llm_google.py`
- [x] `./test_trans.py`

## Backend
### Root & App
- [x] `./backend/requirements.txt`
- [x] `./backend/pyproject.toml`
- [x] `./backend/run.py`
- [x] `./backend/app/__init__.py`
- [x] `./backend/app/config.py`

### Services
- [x] `./backend/app/services/__init__.py`
- [x] `./backend/app/services/simulation_manager.py`
- [x] `./backend/app/services/zep_tools.py`
- [x] `./backend/app/services/report_agent.py`
- [x] `./backend/app/services/simulation_config_generator.py`
- [x] `./backend/app/services/graph_builder.py`
- [x] `./backend/app/services/simulation_ipc.py`
- [x] `./backend/app/services/zep_entity_reader.py`
- [x] `./backend/app/services/zep_graph_memory_updater.py`
- [x] `./backend/app/services/text_processor.py`
- [x] `./backend/app/services/oasis_profile_generator.py`
- [x] `./backend/app/services/ontology_generator.py`
- [x] `./backend/app/services/simulation_runner.py`

### API & Utils & Models
- [x] `./backend/app/api/__init__.py`
- [x] `./backend/app/api/report.py`
- [x] `./backend/app/api/simulation.py`
- [x] `./backend/app/api/graph.py`
- [x] `./backend/app/utils/__init__.py`
- [x] `./backend/app/utils/logger.py`
- [x] `./backend/app/utils/file_parser.py`
- [x] `./backend/app/utils/retry.py`
- [x] `./backend/app/utils/llm_client.py`
- [x] `./backend/app/utils/zep_paging.py`
- [x] `./backend/app/models/__init__.py`
- [x] `./backend/app/models/task.py`
- [x] `./backend/app/models/project.py`

### Scripts
- [x] `./backend/scripts/run_parallel_simulation.py`
- [x] `./backend/scripts/test_profile_format.py`
- [x] `./backend/scripts/run_twitter_simulation.py`
- [x] `./backend/scripts/action_logger.py`
- [x] `./backend/scripts/run_reddit_simulation.py`

## Frontend
### Root & Vue Components
- [x] `./frontend/index.html`
- [x] `./frontend/src/App.vue`
- [x] `./frontend/src/components/Step2EnvSetup.vue`
- [x] `./frontend/src/components/Step5Interaction.vue`
- [x] `./frontend/src/components/Step3Simulation.vue`
- [x] `./frontend/src/components/HistoryDatabase.vue`
- [x] `./frontend/src/components/GraphPanel.vue`
- [x] `./frontend/src/components/Step4Report.vue`
- [x] `./frontend/src/components/Step1GraphBuild.vue`

### API & Store
- [x] `./frontend/src/api/index.js`
- [x] `./frontend/src/api/graph.js`
- [x] `./frontend/src/api/simulation.js`
- [x] `./frontend/src/api/report.js`
- [x] `./frontend/src/store/pendingUpload.js`

### Views
- [x] `./frontend/src/views/ReportView.vue`
- [x] `./frontend/src/views/InteractionView.vue`
- [x] `./frontend/src/views/SimulationView.vue`
- [x] `./frontend/src/views/Home.vue`
- [x] `./frontend/src/views/Process.vue`
- [x] `./frontend/src/views/SimulationRunView.vue`
- [x] `./frontend/src/views/MainView.vue`
