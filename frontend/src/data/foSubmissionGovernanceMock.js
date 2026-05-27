/**

 * 功能 FO 提交生命周期填报后：分类分级与安全要求识别（后端 evaluate + 门户规则试算）。

 */



import { evaluateSecurityRequirements } from "../api/dsmsSpaceApi.js";

import { getPortalTenantIds } from "../composables/usePortalTenantContext.js";

import { loadDataFieldCatalogEntries } from "./dataFieldCatalogMock.js";

import { LIFECYCLE_BUILTIN_DATA_FIELD_KEY } from "./lifecycleFieldConfigMock.js";
import { describeFieldGovernanceSnapshot } from "./securityConditionCatalog.js";

import {

  evaluateRulesForField,

  formatRuleActionPreview,

  loadSecurityRequirementRules

} from "./securityRequirementRulesMock.js";

import { formatTaxonomyPathByCode } from "./taxonomyNodeMock.js";



function stripHtml(html) {

  return String(html || "")

    .replace(/<[^>]+>/g, " ")

    .replace(/\s+/g, " ")

    .trim();

}



/** @param {string} label */

function catalogEntryByLabel(label) {

  const lab = String(label || "").trim();

  return loadDataFieldCatalogEntries().find((e) => e.label === lab) || null;

}



/**

 * 将明细表行中的动态列写入字段生命周期取值（供安全要求规则求值）。

 * @param {Record<string, unknown>[]} rows

 */

/** 生命周期取值由后端任务字段承载；不再写入 sessionStorage。 */
export function persistFieldLifecycleValuesFromFillRows(_rows) {
  /* no-op */
}



/**

 * @param {Record<string, unknown>[]} lifecycleRows

 */

export async function evaluateGovernanceForLifecycleRows(lifecycleRows) {

  const rules = loadSecurityRequirementRules();

  const { tenantId, spaceId } = getPortalTenantIds();

  const seen = new Set();

  /** @type {object[]} */

  const fields = [];



  for (const row of lifecycleRows || []) {

    const label = String(row[LIFECYCLE_BUILTIN_DATA_FIELD_KEY] || "").trim();

    if (!label || seen.has(label)) continue;

    seen.add(label);

    const entry = catalogEntryByLabel(label);

    const fieldId = entry?.id || "";

    const snap = fieldId ? describeFieldGovernanceSnapshot(fieldId) : { gradeLabel: "—", taxPath: "—" };

    const triggeredRules = [];



    if (fieldId) {

      for (const t of evaluateRulesForField(fieldId, rules).filter((r) => r.triggered)) {

        triggeredRules.push({

          ruleName: t.rule.rule_name,

          actionPreview: stripHtml(formatRuleActionPreview(t.rule)) || "（未填写）"

        });

      }

    }



    const apiId = entry?._apiId || (fieldId ? Number(fieldId) : null);

    if (apiId && tenantId && spaceId) {

      try {

        const data = await evaluateSecurityRequirements(tenantId, spaceId, [Number(apiId)]);

        const item = (data?.items || []).find((x) => x.field_catalog_entry_id === Number(apiId));

        if (item) {

          for (const req of item.requirements || []) {

            if (!req.passed) {

              triggeredRules.push({

                ruleName: req.requirement_name,

                actionPreview: req.reason || "未满足"

              });

            }

          }

        }

      } catch {

        /* 求值失败时保留门户规则结果 */

      }

    }



    fields.push({

      fieldLabel: label,

      fieldId: fieldId || "",

      gradeLabel: snap.gradeLabel,

      taxPath: entry?.taxonomy_code ? formatTaxonomyPathByCode(entry.taxonomy_code) : snap.taxPath,

      triggeredRules

    });

  }



  const withRules = fields.filter((f) => f.triggeredRules.length).length;

  return {

    evaluatedAt: new Date().toISOString().slice(0, 16).replace("T", " "),

    fields,

    summaryMessage: `已对 ${fields.length} 个数据字段完成分类分级查阅与安全要求识别；其中 ${withRules} 个字段命中至少一条安全要求。`

  };

}


