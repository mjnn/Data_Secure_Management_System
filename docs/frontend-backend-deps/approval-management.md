# 审批管理 — 后端依赖清单

## 1. 前端入口

- **路由**：`/approval`，`name`: `dashboard-approval`
- **页面**：`frontend/src/views/ApprovalManagementPage.vue`
- **审批链说明**：`frontend/src/data/approvalChains.js`
- **类型/状态常量**：`frontend/src/data/approvalRequestsMock.js`（仅展示标签，无 sessionStorage）

## 2. 审批链（角色）

| 事项 | 发起方 | 审批方 |
|------|--------|--------|
| 业务功能绑定/解绑 | 功能 FO | 数据安全 FO |
| 数据字段新增/删除 | 功能 FO | 数据安全 FO |
| 取消填报任务 | 功能 FO | 数据安全 FO |
| 填报内容审核 | FO 提交后挂起 | 数据安全 FO |
| 填报任务下发 | 数据安全 FO | —（非审批，按业务功能下发） |

## 3. 当前实现状态

- **已接 API**（`portalApi.js` + `usePortalTenantContext`）：
  - `GET .../approval-requests` — 列表/筛选
  - `POST .../approval-requests/{id}/approve|reject` — 通过/驳回
  - `GET .../approval-requests/pending-count` — 侧栏与首页红点
  - FO 绑定申请：`POST .../fo-function-binding-requests`（`FoBusinessFunctionBindingCard`）
  - 字段目录申请：审批记录由后端创建（`FieldCatalogPage` 不再写本地 mock）
  - 取消填报：`POST .../submission-tasks/{id}/cancel-request`
  - 填报审核：`submission_fill_review`，详情页 `approveApprovalRequest` / `rejectApprovalRequest`
- **仍 Mock**：审批链一览文案（`approvalChains.js`）

## 4. 待接 / 收敛项

- 绑定/字段/取消等待办 payload 已在 `approval_to_dict` 对齐

## 5. 联调检查清单

- [ ] 绑定申请通过后 `GET .../fo-function-bindings/me` 与列表一致
- [ ] 驳回须填写理由（中文）
- [ ] 填报审核与任务 `auditStatus` 双向一致
