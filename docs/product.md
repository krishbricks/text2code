# Product Requirements Document: Text2Code Generator

## Executive Summary

### Problem Statement
Data engineers spend significant time writing repetitive PySpark ETL code for data transformations. Translating column mapping specifications into production-ready PySpark scripts is time-consuming, error-prone, and requires deep Databricks expertise.

### Solution
Text2Code Generator is a web-based application that automatically generates production-ready PySpark ETL code from CSV mapping specifications using AI (Claude Sonnet 4.5). Users upload mapping CSVs, select ETL patterns, and receive syntactically correct, tested PySpark code ready for deployment to Databricks.

### Key Value Propositions
- **10x Faster Development**: Generate PySpark pipelines in seconds instead of hours
- **Zero Coding Required**: Business analysts can create ETL pipelines without Python knowledge
- **Best Practices Built-in**: Generated code follows Databricks best practices for Unity Catalog, Delta Lake, and performance
- **Deployment Ready**: Code includes error handling, logging, parameterization, and unit tests
- **Version Control**: Track all generated code versions with full history and rollback capabilities

---

## Target Users

### Primary Persona: Data Engineer
- **Need**: Quickly scaffold PySpark ETL pipelines from business requirements
- **Pain Points**: Repetitive coding, maintaining consistency across pipelines, writing unit tests
- **Goals**: Generate boilerplate code fast, customize generated code, deploy to production quickly

### Secondary Persona: Business Analyst
- **Need**: Create simple data transformations without coding
- **Pain Points**: Dependency on engineers for simple mappings, long development cycles
- **Goals**: Self-serve ETL creation for reporting and analytics use cases

### Tertiary Persona: Data Architect
- **Need**: Ensure consistent patterns and best practices across all ETL pipelines
- **Pain Points**: Code quality variance, missing error handling, non-standard approaches
- **Goals**: Standardize ETL patterns, enforce best practices, maintain code quality

---

## Core Features

### 1. Code Generation Engine

#### Mapping CSV Upload
- **Description**: Users upload CSV files defining source-to-target column mappings
- **CSV Format**:
  ```
  Source_Table,Source_Column,Target_Table,Target_Column,Transformation
  /Volumes/catalog/schema/bronze/sales,order_id,/Volumes/catalog/schema/silver/orders,order_key,
  /Volumes/catalog/schema/bronze/sales,amount,/Volumes/catalog/schema/silver/orders,total_amount,amount * 1.1
  ```
- **Validation**: Schema validation, path verification, transformation syntax checking
- **User Stories**:
  - As a data engineer, I want to upload mapping CSVs so that I can generate PySpark code without manual coding
  - As a business analyst, I want clear error messages when my CSV format is incorrect so I can fix it myself

#### Pattern Library Selection
- **Description**: Users select from predefined ETL patterns that determine code generation strategy
- **Available Patterns**:
  - **Full Load (Overwrite)**: Simple overwrite of target table
  - **Incremental (Append)**: Append new records based on timestamp/ID
  - **Upsert (MERGE)**: Update existing records, insert new ones using Delta MERGE
  - **SCD Type 2**: Slowly Changing Dimension with history tracking
  - **Custom Pattern**: Users define their own pattern with custom prompt
- **User Stories**:
  - As a data engineer, I want to select MERGE pattern so I can generate upsert logic automatically
  - As a data architect, I want to create custom patterns so my team follows our organization's standards

#### AI-Powered Code Generation
- **Description**: Uses Claude Sonnet 4.5 via Databricks Model Serving to generate PySpark code
- **Model Configuration**:
  - Model: `databricks-claude-sonnet-4-5` (Foundation Model API)
  - Temperature: 0.05 (deterministic output)
  - Max tokens: 4000
- **Generated Code Includes**:
  - Source data reading from Unity Catalog Volumes
  - Column transformations and business logic
  - Target data writing with Delta Lake
  - Error handling and logging
  - Parameterization with dbutils.widgets
  - Idempotent execution logic
- **User Stories**:
  - As a data engineer, I want generated code to include error handling so I don't have to add it manually
  - As a business analyst, I want code that works in Databricks notebooks without modification

### 2. Code Preview & Editing

#### Syntax-Highlighted Preview
- **Description**: Display generated code with Python syntax highlighting before saving
- **Features**:
  - Line numbers
  - Collapsible code sections
  - Copy to clipboard
  - Download as .py file
- **User Stories**:
  - As a data engineer, I want to preview generated code so I can verify it meets my requirements before using it

#### In-Browser Code Editor
- **Description**: Edit generated code directly in the web UI with Monaco Editor (VS Code engine)
- **Features**:
  - Python IntelliSense
  - Syntax validation
  - Find/Replace
  - Undo/Redo
  - Format code
- **User Stories**:
  - As a data engineer, I want to make small tweaks to generated code so I don't have to download and re-upload it

### 3. Unit Test Generation

#### Automated Test Creation
- **Description**: Generate pytest unit tests for generated PySpark code
- **Test Coverage**:
  - Schema validation tests
  - Transformation logic tests
  - Edge case handling (nulls, duplicates)
  - Data quality checks
- **Test Framework**: pytest + chispa (PySpark testing library)
- **User Stories**:
  - As a data engineer, I want unit tests generated automatically so I can ensure code quality without extra work
  - As a data architect, I want test coverage reports so I can enforce quality standards

### 4. Deployment Automation

#### Direct Databricks Deployment
- **Description**: Deploy generated code directly to Databricks as notebooks or workflow tasks
- **Deployment Options**:
  - **Save to Workspace**: Write notebook to `/Workspace/Users/{user}/generated_pipelines/`
  - **Save to Volume**: Write .py file to Unity Catalog Volume
  - **Create Workflow**: Create Databricks Job with generated code as task
  - **Add to Existing Workflow**: Add as new task to existing job
- **Parameterization**: Auto-configure job parameters from dbutils.widgets
- **User Stories**:
  - As a data engineer, I want to deploy code to a workspace notebook so I can test it immediately
  - As a data engineer, I want to create a scheduled job so my pipeline runs automatically

### 5. History & Versioning

#### Code Generation History
- **Description**: Track all code generations with metadata for auditability and rollback
- **Tracked Metadata**:
  - Timestamp
  - User (Databricks email)
  - Mapping CSV used
  - Pattern selected
  - Model version
  - Generated code (full text)
- **Storage**: DuckDB embedded database or Delta table in Unity Catalog
- **User Stories**:
  - As a data engineer, I want to see my generation history so I can reuse previous configurations
  - As a data architect, I want to audit who generated what code for compliance purposes

#### Version Diff Viewer
- **Description**: Compare different versions of generated code side-by-side
- **Features**:
  - Side-by-side diff view
  - Inline diff highlighting
  - Rollback to previous version
  - Export diff as text
- **User Stories**:
  - As a data engineer, I want to compare two versions so I can understand what changed in the generation logic

---

## User Workflows

### Workflow 1: Basic Code Generation
1. User logs into Text2Code Generator web app (Databricks SSO)
2. User uploads mapping CSV file
3. App validates CSV schema and displays preview
4. User selects "Full Load (Overwrite)" pattern
5. User clicks "Generate Code"
6. App calls Claude Sonnet 4.5 and displays generated PySpark code
7. User reviews code in syntax-highlighted preview
8. User downloads .py file or deploys to workspace

### Workflow 2: Advanced Generation with Tests
1. User uploads mapping CSV
2. User selects "Upsert (MERGE)" pattern
3. User enables "Generate Unit Tests" option
4. User customizes prompt template (optional)
5. User clicks "Generate Code & Tests"
6. App generates both PySpark code and pytest tests
7. User edits code in Monaco Editor to add custom business logic
8. User downloads both .py and test file
9. User deploys code to Unity Catalog Volume
10. User creates Databricks Workflow with generated code

### Workflow 3: Version Management
1. User navigates to "History" page
2. User sees list of all previous generations (timestamp, pattern, status)
3. User clicks on a previous generation to view details
4. User clicks "Compare with Latest" to see diff
5. User clicks "Rollback to This Version" to regenerate code from this configuration
6. App re-generates code using stored mapping CSV and pattern

---

## Success Metrics

### Primary Metrics
- **Generation Success Rate**: % of successful code generations (target: >95%)
- **User Adoption**: Number of active users generating code weekly (target: 50+ users)
- **Code Quality**: % of generated code deployed to production without modification (target: >60%)
- **Time Saved**: Average time from mapping to deployed code (target: <5 minutes)

### Secondary Metrics
- **Pattern Usage**: Distribution of pattern selection to identify most valuable patterns
- **Edit Rate**: % of users who edit generated code before deployment
- **Deployment Rate**: % of generated code that gets deployed to production
- **Error Rate**: % of deployed code that encounters runtime errors

### User Satisfaction Metrics
- **NPS Score**: Net Promoter Score from quarterly surveys (target: >50)
- **Feature Requests**: Number and type of feature requests to prioritize roadmap
- **Support Tickets**: Number of bugs and usability issues reported

---

## Implementation Phases

### Phase 1: MVP (Core Generation) - Weeks 1-2
**Goal**: Basic web UI with code generation capability

**Features**:
- Upload mapping CSV
- Select pattern (Full Load, Incremental only)
- Generate PySpark code using Claude Sonnet 4.5
- Display code with syntax highlighting
- Download generated code

**Success Criteria**:
- Users can upload CSV and generate working PySpark code
- Generated code runs successfully in Databricks notebooks
- 10 users successfully generate and deploy code

### Phase 2: Enhanced UX (Preview & Editing) - Weeks 3-4
**Goal**: Improve user experience with editing and better previews

**Features**:
- Monaco Editor for in-browser code editing
- Code preview with collapsible sections
- All ETL patterns (MERGE, SCD2, Custom)
- Save to Databricks Workspace
- Deploy to Unity Catalog Volume

**Success Criteria**:
- 50% of users edit code before deployment
- All 5 patterns are used in production
- Deployment automation works for 90%+ of users

### Phase 3: Quality & Automation (Tests & Deployment) - Weeks 5-6
**Goal**: Add testing and deployment automation

**Features**:
- Unit test generation
- Create Databricks Workflow from generated code
- Add to existing workflow
- Parameterization UI for job configuration
- Test execution report

**Success Criteria**:
- 70% of generated code includes unit tests
- 40% of users deploy directly to workflows
- Generated tests have >80% pass rate

### Phase 4: Version Control (History & Diff) - Weeks 7-8
**Goal**: Add versioning and auditability

**Features**:
- Generation history tracking
- Version diff viewer
- Rollback functionality
- Audit logs for compliance
- Search and filter history

**Success Criteria**:
- All generations are tracked in history
- 20% of users use diff viewer
- Zero data loss in version tracking

---

## Technical Constraints

### Databricks-Specific Requirements
- Must authenticate using Databricks SSO (OAuth)
- Must use Databricks personal access tokens for API calls
- Must support Unity Catalog Volume paths (`/Volumes/catalog/schema/volume/`)
- Must use Foundation Model API for Claude Sonnet 4.5
- Generated code must be compatible with Databricks Runtime 13.3+

### Security & Compliance
- No storage of raw data (only mapping metadata)
- All code generation must be auditable
- Must support role-based access control (RBAC)
- Generated code must not contain hardcoded credentials
- Must comply with data residency requirements (Azure only, no cross-region)

### Performance Requirements
- Code generation: <30 seconds for typical mapping (50 columns)
- File upload: Support CSV files up to 10MB
- Concurrent users: Support 50 simultaneous generations
- History search: <2 seconds for 1000+ generations

---

## Out of Scope (Future Considerations)

### Not in Initial Release
- **Multi-language support**: Only Python/PySpark in v1 (SQL, Scala later)
- **Real-time collaboration**: No multi-user editing of same mapping
- **Template marketplace**: No public sharing of custom patterns
- **Integration with Git**: No direct GitHub/GitLab integration
- **Scheduling UI**: Use Databricks Workflows for scheduling
- **Data profiling**: No automatic source data analysis
- **Cost estimation**: No compute cost prediction for generated jobs

### Deferred Features
- AI-assisted debugging of generated code
- Natural language to mapping CSV conversion
- Automated performance optimization suggestions
- Integration with data lineage tools (Unity Catalog lineage comes free)

---

## Dependencies

### External Services
- **Databricks Foundation Model API**: Claude Sonnet 4.5 availability
- **Databricks Workspace API**: For deployment to workspace/volumes
- **Databricks Jobs API**: For workflow creation

### User Requirements
- Databricks workspace access with Unity Catalog enabled
- Personal Access Token (PAT) with workspace and volumes permissions
- Browser: Chrome/Edge/Firefox (latest 2 versions)

---

## Risk Mitigation

### Technical Risks
- **LLM hallucination**: Implement code validation and syntax checking before deployment
- **Model availability**: Cache common patterns, provide fallback to last known good configuration
- **API rate limits**: Implement queuing and rate limiting on client side

### User Adoption Risks
- **Learning curve**: Provide interactive tutorial and sample CSVs
- **Trust in AI**: Show generated code diff vs manual code to build confidence
- **Change resistance**: Start with pilot group of early adopters

---

## Appendix: Example Mapping CSV

```csv
Source_Table,Source_Column,Target_Table,Target_Column,Transformation
/Volumes/krish_catalog/krish_schema/test_vol/input/sales.parquet,order_id,/Volumes/krish_catalog/krish_schema/test_vol/output/orders,order_key,
/Volumes/krish_catalog/krish_schema/test_vol/input/sales.parquet,customer_id,/Volumes/krish_catalog/krish_schema/test_vol/output/orders,customer_key,
/Volumes/krish_catalog/krish_schema/test_vol/input/sales.parquet,amount,/Volumes/krish_catalog/krish_schema/test_vol/output/orders,total_amount,amount * 1.1
/Volumes/krish_catalog/krish_schema/test_vol/input/sales.parquet,order_date,/Volumes/krish_catalog/krish_schema/test_vol/output/orders,order_timestamp,to_timestamp(order_date)
/Volumes/krish_catalog/krish_schema/test_vol/input/sales.parquet,,/Volumes/krish_catalog/krish_schema/test_vol/output/orders,load_timestamp,current_timestamp()
```

**Transformation Rules**:
- Empty transformation = direct column mapping
- Python expression = apply transformation (e.g., `amount * 1.1`)
- Empty source column = derived column (e.g., `current_timestamp()`)
