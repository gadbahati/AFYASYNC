export async function quoteBenefit(payload:any){return (await import("./client")).api.benefitQuote(payload)}
export async function listBenefitRules(params:any={}){return (await import("./client")).api.benefitRules(params)}
export async function createBenefitRule(payload:any){return (await import("./client")).api.createBenefitRule(payload)}
