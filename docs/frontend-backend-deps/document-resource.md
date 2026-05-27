# 文档资源 — 前后端依赖清单

| 项 | 值 |
|----|-----|
| 路由 `name` | `dashboard-document-resource` |
| 路径 | `/document-resource` |
| 主要源码 | `DocumentResourcePage.vue`、`usePortalTenantContext.js` |
| 数据模型 | `docs/DSMS_DATA_MODEL.md` §5 |

## 模块职责

1. **法规文件库**：上传/检索/下载数据安全法规与标准文件（PDF、Word 等）。
2. **Excel 枢纽**：各业务模块表数据的模板下载、批量导入、筛选导出。
3. **作业记录**：`document_transfer_job` 状态与结果文件下载。

## 已接 API

| 能力 | 说明 |
|------|------|
| 法规列表 | `GET .../documents/resources?kind=regulation` |
| 上传/下载 | `POST .../documents/resources`；`GET .../resources/{id}/download` |
| 模块注册表 | `GET .../documents/modules` |
| 模板 | `GET .../documents/modules/{module_key}/template` |
| 导入/导出 | `POST .../spaces/{space_id}/documents/import` / `export` |
| 作业列表 | `GET .../documents/jobs` |

Excel 导入已实现：`field_catalog`、`sensitivity_level`；导出已实现全部注册模块（未实现模块导出空表占位）。

## 待完善

前缀：`/api/v1/dsms/tenants/{tenant_id}`；空间级作业：`.../spaces/{space_id}/documents/...`

| 能力 | 方法 | 路径 | 权限（规划） |
|------|------|------|--------------|
| 资源列表 | GET | `/documents/resources` | tenant 成员 |
| 上传法规/文件 | POST | `/documents/resources` | security_fo / tenant_admin |
| 下载 | GET | `/documents/resources/{id}/download` | tenant 成员 |
| 模块能力 | GET | `/documents/modules` | tenant 成员 |
| 导入模板 | GET | `/documents/modules/{module_key}/template` | 按模块 |
| 发起导入 | POST | `/spaces/{space_id}/documents/import` | 按模块 |
| 发起导出 | POST | `/spaces/{space_id}/documents/export` | 按模块 |
| 作业列表 | GET | `/documents/jobs` | tenant 成员 |

Query/Body 要点见 `DSMS_DATA_MODEL.md` §5.5。

## 权限与规格

- 门户角色：`security_fo` 可维护法规与多数导入；`function_fo` 可读法规、按模块只读导出。
- 审计键：`document-resource-upload`、`document-import-start`、`document-export-start`（见数据模型 §6）。

## 与规格的差异

- 原规格 §7.3 配置包导入/导出为 **JSON/ZIP 整包**；本页 Excel 为 **业务人员快捷通道**，二者并存。

## 联调自检项

- [ ] 上传法规 PDF 后列表可检索、可下载
- [ ] 字段主表：下载模板 → 填行 → 导入 → 作业 summary 与 catalog 一致
- [ ] 导出带筛选条件，生成 xlsx 可打开
- [ ] 导入失败时提供 error_report 下载
- [ ] 侧栏「文档资源」与 Tab 路由一致
