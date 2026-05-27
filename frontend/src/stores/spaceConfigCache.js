/** 空间级配置内存缓存（API 拉取后供 mock 加载器与工作流只读）。 */



const cache = {

  questionnaire: [],

  relevanceExpression: null,

  lifecycleFields: [],

  taxonomyNodes: null,

  taxonomyLevels: null,

  sensitivityLevels: null,

  fieldCatalog: null,

  classGrades: null,

  securityRules: null

};



export function setQuestionnaireCache(items) {

  cache.questionnaire = Array.isArray(items) ? items : [];

}



export function getQuestionnaireCache() {

  return cache.questionnaire;

}



export function setRelevanceExpressionCache(expr) {

  cache.relevanceExpression = expr;

}



export function getRelevanceExpressionCache() {

  return cache.relevanceExpression;

}



export function setLifecycleFieldsCache(items) {

  cache.lifecycleFields = Array.isArray(items) ? items : [];

}



export function getLifecycleFieldsCache() {

  return cache.lifecycleFields;

}



export function setTaxonomyNodesCache(items) {

  cache.taxonomyNodes = Array.isArray(items) ? items : [];

}



export function hasTaxonomyNodesCache() {

  return cache.taxonomyNodes !== null;

}



export function getTaxonomyNodesCache() {

  return cache.taxonomyNodes ?? [];

}



export function setTaxonomyLevelsCache(items) {

  cache.taxonomyLevels = Array.isArray(items) ? items : [];

}



export function hasTaxonomyLevelsCache() {

  return cache.taxonomyLevels !== null;

}



export function getTaxonomyLevelsCache() {

  return cache.taxonomyLevels ?? [];

}



export function setSensitivityLevelsCache(items) {

  cache.sensitivityLevels = Array.isArray(items) ? items : [];

}



export function hasSensitivityLevelsCache() {

  return cache.sensitivityLevels !== null;

}



export function getSensitivityLevelsCache() {

  return cache.sensitivityLevels ?? [];

}



export function setFieldCatalogCache(items) {

  cache.fieldCatalog = Array.isArray(items) ? items : [];

}



export function hasFieldCatalogCache() {

  return cache.fieldCatalog !== null;

}



export function getFieldCatalogCache() {

  return cache.fieldCatalog ?? [];

}



export function setClassGradesCache(items) {

  cache.classGrades = Array.isArray(items) ? items : [];

}



export function hasClassGradesCache() {

  return cache.classGrades !== null;

}



export function getClassGradesCache() {

  return cache.classGrades ?? [];

}



export function setSecurityRulesCache(items) {

  cache.securityRules = Array.isArray(items) ? items : [];

}



export function hasSecurityRulesCache() {

  return cache.securityRules !== null;

}



export function getSecurityRulesCache() {

  return cache.securityRules ?? [];

}



export function clearSpaceConfigCache() {

  cache.questionnaire = [];

  cache.relevanceExpression = null;

  cache.lifecycleFields = [];

  cache.taxonomyNodes = null;

  cache.taxonomyLevels = null;

  cache.sensitivityLevels = null;

  cache.fieldCatalog = null;

  cache.classGrades = null;

  cache.securityRules = null;

}


