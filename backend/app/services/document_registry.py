"""文档资源：可导入/导出模块注册表（docs/DSMS_DATA_MODEL.md §5.4）。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentModuleSpec:
    module_key: str
    title: str
    import_enabled: bool
    export_enabled: bool
    template_filename: str


DOCUMENT_MODULES: tuple[DocumentModuleSpec, ...] = (
    DocumentModuleSpec("field_catalog", "数据字段主表", True, True, "field_catalog_template.xlsx"),
    DocumentModuleSpec("field_class_grade", "密级绑定", True, True, "field_class_grade_template.xlsx"),
    DocumentModuleSpec("sensitivity_level", "密级定义", True, True, "sensitivity_level_template.xlsx"),
    DocumentModuleSpec("taxonomy_level", "分类树层级", True, True, "taxonomy_level_template.xlsx"),
    DocumentModuleSpec("taxonomy_node", "分类树节点", True, True, "taxonomy_node_template.xlsx"),
    DocumentModuleSpec("field_taxonomy_binding", "字段—分类绑定", True, True, "field_taxonomy_binding_template.xlsx"),
    DocumentModuleSpec("lifecycle_field_config", "生命周期元字段", True, True, "lifecycle_field_config_template.xlsx"),
    DocumentModuleSpec("relevance_questionnaire", "相关性问卷", True, True, "relevance_questionnaire_template.xlsx"),
    DocumentModuleSpec("business_function", "业务功能", True, True, "business_function_template.xlsx"),
    DocumentModuleSpec("submission_task", "填报任务清单", False, True, "submission_task_export.xlsx"),
    DocumentModuleSpec("classification_matrix", "分类矩阵", True, True, "classification_matrix_template.xlsx"),
    DocumentModuleSpec("classification_result", "分类分级结果", False, True, "classification_result_export.xlsx"),
)


def get_module_spec(module_key: str) -> DocumentModuleSpec | None:
    for m in DOCUMENT_MODULES:
        if m.module_key == module_key:
            return m
    return None


def list_modules_dict() -> list[dict]:
    return [
        {
            "module_key": m.module_key,
            "title": m.title,
            "import_enabled": m.import_enabled,
            "export_enabled": m.export_enabled,
            "template_filename": m.template_filename,
        }
        for m in DOCUMENT_MODULES
    ]
