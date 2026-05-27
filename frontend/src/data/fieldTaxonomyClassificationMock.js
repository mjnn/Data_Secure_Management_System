/**

 * 数据字段 ↔ 分类树（taxonomy_code）— 只读适配层（真源：field_catalog API + spaceConfigCache）。

 */



import { loadDataFieldCatalogEntries, DATA_FIELD_CATALOG_PERSIST_EVENT } from "./dataFieldCatalogMock.js";



export { DATA_FIELD_CATALOG_PERSIST_EVENT };



/** 读取目录并保证含 taxonomy_code */

export function loadFieldCatalogWithTaxonomy() {

  return loadDataFieldCatalogEntries().map((entry) => ({

    ...entry,

    taxonomy_code: entry.taxonomy_code != null ? String(entry.taxonomy_code).trim() : ""

  }));

}


