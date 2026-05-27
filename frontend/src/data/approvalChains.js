/**
 * 各角色审批链说明（门户展示用，与 mock 审批类型一致）。
 */

export const APPROVAL_CHAIN_ROWS = [
  {
    id: "fo_function_binding",
    requestType: "fo_function_binding",
    title: "业务功能绑定 / 解绑",
    applicantRole: "功能 FO",
    approverRole: "数据安全 FO",
    trigger: "功能 FO 在填报任务管理中提交绑定变更申请（增删绑定项均须审批）。",
    outcome: "通过后更新本人已绑定业务功能列表；未通过则保持原绑定。",
    note: "数据安全 FO 按业务功能下发填报任务；仅对已绑定 FO 的功能可下发。"
  },
  {
    id: "field_catalog_create",
    requestType: "field_catalog_create",
    title: "数据字段 — 新增",
    applicantRole: "功能 FO",
    approverRole: "数据安全 FO",
    trigger: "功能 FO 在「数据字段」页申请新增目录项。",
    outcome: "通过后写入数据字段主表；驳回则不变。"
  },
  {
    id: "field_catalog_delete",
    requestType: "field_catalog_delete",
    title: "数据字段 — 删除",
    applicantRole: "功能 FO",
    approverRole: "数据安全 FO",
    trigger: "功能 FO 申请删除可见范围内的目录项。",
    outcome: "通过后从主表移除；驳回则保留。"
  },
  {
    id: "submission_fill_cancel",
    requestType: "submission_fill_cancel",
    title: "取消填报任务",
    applicantRole: "功能 FO",
    approverRole: "数据安全 FO",
    trigger: "功能 FO 对未结束的下发任务提交取消申请并填写理由。",
    outcome: "通过后任务对 FO 关闭（已取消）；驳回则继续原进度。"
  },
  {
    id: "submission_fill_review",
    requestType: "submission_fill_review",
    title: "填报内容审核",
    applicantRole: "功能 FO（提交后系统自动挂起）",
    approverRole: "数据安全 FO",
    trigger: "功能 FO 完成相关性 / 生命周期填报并提交后，生成待审核记录。",
    outcome: "通过：填报记为已审核，可纳入「已审核填报」汇总；退回：FO 需修改后再次提交（模拟为退回状态）。"
  },
  {
    id: "submission_task_dispatch",
    requestType: null,
    title: "填报任务下发",
    applicantRole: "数据安全 FO",
    approverRole: "—（非审批）",
    trigger: "数据安全 FO 在「填报任务管理」对草稿任务填写说明后下发。",
    outcome: "任务变为已下发；须该业务功能已绑定功能 FO。",
    note: "属管理动作，不走审批中心。"
  }
];

/** @param {string} type */
export function chainMetaForType(type) {
  return APPROVAL_CHAIN_ROWS.find((r) => r.requestType === type) || null;
}
