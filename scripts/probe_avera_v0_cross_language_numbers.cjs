"use strict";

const fs=require("node:fs");
const crypto=require("node:crypto");

function sortRec(value){
  if(Array.isArray(value)) return value.map(sortRec);
  if(value && typeof value==="object"){
    const out={};
    for(const key of Object.keys(value).sort()) out[key]=sortRec(value[key]);
    return out;
  }
  return value;
}

function jsDigest(envelope){
  const payload={...envelope};
  delete payload.digest;
  const text=JSON.stringify(sortRec(payload));
  return crypto.createHash("sha256").update(Buffer.from(text,"utf8")).digest("hex");
}

const vectors=JSON.parse(fs.readFileSync("avera-v0-cross-language-vectors.json","utf8"));
const results=vectors.map(v=>{
  const observed=jsDigest(v.envelope);
  return {
    confidence_score:v.confidence_score,
    python_digest:v.python_digest,
    js_digest:observed,
    match:observed===v.python_digest
  };
});

const byScore=new Map(results.map(x=>[String(x.confidence_score),x]));
if(!byScore.get("0.66")?.match) throw new Error("0.66 control must match");
if(results.filter(x=>x.match).length!==1) throw new Error("expected exactly one matching vector");

console.log(JSON.stringify({
  avera_v0_cross_language_numeric_boundary:"REPRODUCED",
  cases:results,
  mismatches:results.filter(x=>!x.match).map(x=>x.confidence_score)
}));
