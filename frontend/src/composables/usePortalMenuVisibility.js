/** 门户侧栏菜单与平台角色（后端 /api/v1/users/me 的 platform_role + is_superuser） */

export const PLATFORM_ROLE = {
  SYSTEM_ADMIN: "system_admin",
  SECURITY_FO: "security_fo",
  FUNCTION_FO: "function_fo"
};

export function effectivePlatformRole(me) {
  if (!me) return null;
  if (me.is_superuser) return PLATFORM_ROLE.SYSTEM_ADMIN;
  const pr = me.platform_role;
  if (pr === PLATFORM_ROLE.SYSTEM_ADMIN || pr === PLATFORM_ROLE.SECURITY_FO || pr === PLATFORM_ROLE.FUNCTION_FO) {
    return pr;
  }
  return PLATFORM_ROLE.SECURITY_FO;
}

/**
 * 规则：
 * - 系统管理员：全部（含「项目管理」「填报管理」下各子项）
 * - 数据安全 FO：含「用户管理」「填报管理」（填报情况 + **填报任务管理**）；**不含**「项目管理」
 * - 功能 FO：含「填报管理」下 **仅「填报任务管理」**（不含「填报情况」）；其余同原字段/文档/审批等入口
 */
export function menuVisibilityForRole(role) {
  const isAdmin = role === PLATFORM_ROLE.SYSTEM_ADMIN;
  const isSecurityFo = role === PLATFORM_ROLE.SECURITY_FO;
  const isFunctionFo = role === PLATFORM_ROLE.FUNCTION_FO;
  const secOrAdmin = isAdmin || isSecurityFo;

  return {
    home: true,
    userManagement: isAdmin || isSecurityFo,
    projectManagement: isAdmin,
    submissionParent: secOrAdmin || isFunctionFo,
    submissionStatus: secOrAdmin,
    submissionTask: secOrAdmin || isFunctionFo,
    fieldParent: secOrAdmin || isFunctionFo,
    fieldLifecycle: secOrAdmin,
    fieldCatalog: true,
    ruleGovernance: secOrAdmin,
    documentResource: true,
    approval: true
  };
}
