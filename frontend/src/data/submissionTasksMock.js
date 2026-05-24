/** 填报任务管理：与 sessionStorage 对齐的模拟数据与归一化（列表页 + 详情页共用） */

export const SUBMISSION_TASKS_STORAGE_KEY = "dsms_mock_submission_tasks_v1";

export const MOCK_SUBMISSION_FUNCTIONS = [
  { id: "f_usage", name: "字段填报", key: "field_usage", functionFoBound: true, foDisplay: "function_fo" },
  { id: "f_report", name: "用量上报", key: "usage_report", functionFoBound: false, foDisplay: "" },
  { id: "f_req", name: "字段申请", key: "field_request", functionFoBound: true, foDisplay: "function_fo" }
];

export function submissionFunctionById(id) {
  return MOCK_SUBMISSION_FUNCTIONS.find((f) => f.id === id) || null;
}

export function submissionFunctionName(id) {
  return submissionFunctionById(id)?.name || id;
}

export function submissionTaskRowHasBoundFo(row) {
  return !!submissionFunctionById(row.functionId)?.functionFoBound;
}

/** 是否存在可渲染的填报表单只读快照（sections 或 lifecycle 明细表） */
export function hasRenderableFormSnapshot(snapshot) {
  if (!snapshot) return false;
  if (
    snapshot.formTable &&
    Array.isArray(snapshot.formTable.columns) &&
    snapshot.formTable.columns.length &&
    Array.isArray(snapshot.formTable.rows) &&
    snapshot.formTable.rows.length
  ) {
    return true;
  }
  return Array.isArray(snapshot.sections) && snapshot.sections.some((s) => s?.fields?.length);
}

/**
 * @param {object} t
 * @returns {object}
 */
export function normalizeSubmissionTask(t) {
  const row = { ...t };
  if (row.status === "dispatched" && row.foFillStatus == null) {
    row.foFillStatus = "not_started";
  }
  if (row.foCancellationRequested == null) {
    row.foCancellationRequested = false;
  }
  if (row.foCancellationReason == null) {
    row.foCancellationReason = "";
  }
  if (row.auditStatus == null) {
    row.auditStatus = null;
  }
  if (row.auditComment == null) {
    row.auditComment = "";
  }
  if (row.auditedAt == null) {
    row.auditedAt = null;
  }
  if (row.foFillFormSnapshot === undefined) {
    row.foFillFormSnapshot = null;
  }
  if (row.foFillLifecycleRows === undefined) {
    row.foFillLifecycleRows = null;
  }
  return row;
}

/** 与 `SubmissionTaskManagementPage` 原种子一致，供首次进入或空存储时写入 sessionStorage */
export function buildDefaultSubmissionTasksSeed() {
  const today = new Date().toISOString().slice(0, 10);
  return [
    {
      id: 1,
      functionId: "f_usage",
      title: "Q1 字段填报收集",
      internalNote: "研发条线",
      status: "draft",
      dispatchNote: null,
      dispatchedAt: null,
      createdAt: today
    },
    {
      id: 2,
      functionId: "f_usage",
      title: "试点空间填报",
      internalNote: "",
      status: "dispatched",
      dispatchNote: "请于周五前完成试点空间内全部主数据字段填报。",
      dispatchedAt: "2026-01-10",
      createdAt: "2026-01-08",
      foFillStatus: "submitted",
      foFillContentSummary: "（模拟）已提交：关键字段已填报完成。",
      foFillFormSnapshot: {
        versionKey: "field_usage@v2026-demo",
        submittedAt: "2026-01-10 16:20",
        sections: [
          {
            heading: "填报主体",
            fields: [
              { label: "填报部门", value: "研发数据治理组" },
              { label: "填报人", value: "功能 FO（模拟账号）" },
              { label: "联系电话", value: "021-0000-0000" }
            ]
          },
          {
            heading: "试点空间范围",
            fields: [
              { label: "空间名称", value: "动力总成主数据空间" },
              { label: "是否含子空间", value: "是" },
              { label: "备注", value: "与下发说明一致，覆盖主数据字段清单 A1–A12。" }
            ]
          },
          {
            heading: "字段填报确认（节选）",
            fields: [
              { label: "主数据字段完整性", value: "已核对" },
              { label: "敏感字段脱敏", value: "已按规范处理" },
              { label: "附件", value: "（模拟）无上传，正式流程由附件控件承载" }
            ]
          }
        ]
      },
      foExtraAssignees: [
        {
          label: "协同填报人（模拟）",
          foFillStatus: "draft",
          foCancellationRequested: false,
          foCancellationReason: "",
          foFillContentSummary: "",
          foFillFormSnapshot: {
            versionKey: "field_usage@coassign-draft",
            submittedAt: null,
            sections: [
              {
                heading: "协同补充（草稿）",
                fields: [{ label: "协同说明", value: "（模拟）草稿阶段，待协同人完成后与主责合并展示。" }]
              }
            ]
          }
        }
      ],
      foFillLifecycleRows: [
        { data_field: "主数据字段：客户编号", business_function: "f_usage" },
        { data_field: "主数据字段：车辆 VIN", business_function: "f_usage" },
        { data_field: "主数据字段：动力总成件号", business_function: "f_req" }
      ],
      auditStatus: "approved",
      auditComment: "已审核通过（模拟）。",
      auditedAt: "2026-01-11"
    },
    {
      id: 3,
      functionId: "f_req",
      title: "新字段申请复核",
      internalNote: "",
      status: "draft",
      dispatchNote: null,
      dispatchedAt: null,
      createdAt: today
    },
    {
      id: 4,
      functionId: "f_usage",
      title: "合规自查填报（待开始）",
      internalNote: "",
      status: "dispatched",
      dispatchNote: "请按附件清单完成本季度合规自查项填报。",
      dispatchedAt: today,
      foFillStatus: "not_started"
    },
    {
      id: 5,
      functionId: "f_req",
      title: "主数据变更同步",
      internalNote: "",
      status: "dispatched",
      dispatchNote: "与上游主数据对齐后填报变更说明。",
      dispatchedAt: today,
      foFillStatus: "draft",
      foFillContentSummary: ""
    }
  ];
}

/**
 * 读取 sessionStorage 中的填报任务；若无或为空则写入默认种子并返回。
 * @returns {object[]}
 */
export function loadSubmissionTasksMerged() {
  try {
    const raw = sessionStorage.getItem(SUBMISSION_TASKS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.map(normalizeSubmissionTask);
      }
    }
  } catch (_e) {
    /* ignore */
  }
  const normalized = buildDefaultSubmissionTasksSeed().map(normalizeSubmissionTask);
  try {
    sessionStorage.setItem(SUBMISSION_TASKS_STORAGE_KEY, JSON.stringify(normalized));
  } catch (_e) {
    /* ignore */
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("dsms-submission-tasks-persisted"));
  }
  return normalized;
}
