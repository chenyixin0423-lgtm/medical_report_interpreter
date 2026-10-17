"""Conservative bilingual aliases: no fuzzy matches or merged analytes."""
import re
import unicodedata

CATALOG = {
    "TC": ("Total cholesterol", "总胆固醇|胆固醇|CHOL|TCHO"),
    "LDL": ("LDL cholesterol", "低密度脂蛋白胆固醇|LDL-C|LDLC|low density lipoprotein cholesterol"),
    "HDL": ("HDL cholesterol", "高密度脂蛋白胆固醇|HDL-C|HDLC|high density lipoprotein cholesterol"),
    "TG": ("Triglycerides", "甘油三酯|triglyceride|TRIG"),
    "WBC": ("White blood cell count", "白细胞|白细胞计数|leukocytes"),
    "RBC": ("Red blood cell count", "红细胞|红细胞计数|erythrocytes"),
    "HGB": ("Hemoglobin", "血红蛋白|血红蛋白浓度|HB|haemoglobin"),
    "HCT": ("Hematocrit", "红细胞压积|红细胞比容|PCV|haematocrit"),
    "MCV": ("Mean corpuscular volume", "平均红细胞体积|红细胞平均体积"),
    "MCH": ("Mean corpuscular hemoglobin", "平均红细胞血红蛋白量"),
    "MCHC": ("Mean corpuscular hemoglobin concentration", "平均红细胞血红蛋白浓度"),
    "PLT": ("Platelet count", "血小板|血小板计数|platelets"),
    "NEUT": ("Neutrophils", "中性粒细胞|neutrophil|NEUT#|NEUT%|中性粒细胞计数|中性粒细胞百分比|neutrophil count"),
    "LYMPH": ("Lymphocytes", "淋巴细胞|lymphocyte|LYMPH#|LYMPH%|淋巴细胞计数|淋巴细胞百分比"),
    "MONO": ("Monocytes", "单核细胞|monocyte|MONO#|MONO%|单核细胞计数|单核细胞百分比"),
    "EOS": ("Eosinophils", "嗜酸性粒细胞|eosinophil|EOS#|EOS%|嗜酸性粒细胞计数|嗜酸性粒细胞百分比"),
    "ALT": ("Alanine aminotransferase", "丙氨酸氨基转移酶|谷丙转氨酶|GPT|SGPT"),
    "AST": ("Aspartate aminotransferase", "天门冬氨酸氨基转移酶|谷草转氨酶|GOT|SGOT"),
    "GGT": ("Gamma-glutamyl transferase", "γ-谷氨酰转移酶|谷氨酰转肽酶|gamma glutamyl transferase"),
    "ALP": ("Alkaline phosphatase", "碱性磷酸酶"),
    "TBIL": ("Total bilirubin", "总胆红素"),
    "DBIL": ("Direct bilirubin", "直接胆红素"),
    "IBIL": ("Indirect bilirubin", "间接胆红素"),
    "ALB": ("Albumin", "白蛋白"),
    "TP": ("Total protein", "总蛋白"),
    "BUN": ("Blood urea nitrogen", "尿素氮|urea nitrogen"),
    "CREA": ("Serum creatinine", "肌酐|血清肌酐|SCr|creatinine"),
    "UA": ("Uric acid", "尿酸|URIC"),
    "eGFR": ("Estimated glomerular filtration rate", "估算肾小球滤过率|估算的肾小球滤过率"),
    "GLU": ("Glucose", "葡萄糖|血糖|fasting blood glucose|FBG|FPG|空腹血糖"),
    "HbA1c": ("Glycated hemoglobin", "糖化血红蛋白|hemoglobin a1c|glycosylated hemoglobin"),
}


def key(name: str) -> str:
    return re.sub(r"[\s_\-()（）]", "", unicodedata.normalize("NFKC", name).casefold())


ALIASES = {key(alias): code for code, (name, aliases) in CATALOG.items()
           for alias in [code, name, *aliases.split("|")]}


def normalize(name: str) -> str | None:
    direct = ALIASES.get(key(name))
    if direct:
        return direct
    # A bilingual label must agree, e.g. 白细胞(WBC); don't guess substrings.
    parts = re.split(r"[()（）]", name)
    codes = [ALIASES.get(key(p)) for p in parts if p.strip()]
    if codes and all(c is not None and c == codes[0] for c in codes):
        return codes[0]
    return None
