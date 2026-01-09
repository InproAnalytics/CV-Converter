# tech_mapping.py


# ===== MAPPING =====
TECH_MAPPING = {
    # ===== Programming Languages =====
    r"(?i)\bpython\b": "programming_languages",
    r"(?i)\bjavascript\b": "programming_languages",
    r"(?i)\btypescript\b": "programming_languages",
    r"(?i)\bsql\b": "programming_languages",
    r"(?i)\bbash\b": "programming_languages",
    r"(?i)\bnode(\.js)?\b": "programming_languages",
    r"(?i)\bjava\b": "programming_languages",
    r"(?i)\bgo(lang)?\b": "programming_languages",
    r"(?i)(?<!\w)c\+\+(?!\w)": "programming_languages",   # fixed
    r"(?i)(?<!\w)c#(?!\w)": "programming_languages",     # fixed
    r"(?i)\bruby\b": "programming_languages",
    r"(?i)\bscala\b": "programming_languages",
    r"(?i)\br\b": "programming_languages",

    # ===== Backend =====
    r"(?i)\bdjango(\s*/\s*django\s*rest|\s+rest(\s+framework)?)?\b": "backend",
    r"(?i)\bfastapi\b": "backend",
    r"(?i)\bflask\b": "backend",
    r"(?i)\bcelery\b": "backend",
    r"(?i)\bsqlalchemy\b": "backend",
    r"(?i)\baiohttp\b": "backend",
    r"(?i)\bmicroservices?\b": "backend",
    r"(?i)\bapi\b": "backend",
    r"(?i)\bbeautiful\s*soup\b": "backend",
    r"(?i)\bclean\s*architecture\b": "backend",
    r"(?i)\bsolid\b": "backend",
    r"(?i)\bmvc\b": "backend",
    r"(?i)\bweb\s*socket\b": "backend",

    # ===== Frontend =====
    r"(?i)\breact(\.js)?\b": "frontend",
    r"(?i)\bnext(\.js)?\b": "frontend",
    r"(?i)\bredux\b": "frontend",
    r"(?i)\bvue(\.js)?\b": "frontend",
    r"(?i)\bangular\b": "frontend",
    r"(?i)\bhtml\b": "frontend",
    r"(?i)\bcss\b": "frontend",
    r"(?i)\bscss\b": "frontend",
    r"(?i)\bmaterial\s*ui\b": "frontend",
    r"(?i)\bant\s*design\b": "frontend",
    r"(?i)\bag\s*grid\b": "frontend",

    # ===== Databases =====
    r"(?i)\b(postgres|postgresql)\b": "databases",
    r"(?i)\bmysql\b": "databases",
    r"(?i)\bredis\b": "databases",
    r"(?i)\bmongodb\b": "databases",
    r"(?i)\belasticsearch\b": "databases",
    r"(?i)\bsnowflake\b": "databases",
    r"(?i)\bsql\s*server\b": "databases",
    r"(?i)\boracle\b": "databases",
    r"(?i)\bcassandra\b": "databases",
    r"(?i)\bbigquery\b": "databases",
    r"(?i)\bpgvector\b": "databases",

    # ===== Data Engineering =====
    r"(?i)\bazure\s+(data\s+factory|synapse|data\s+lake|databricks)\b": "data_engineering",
    r"(?i)\bspark\b": "data_engineering",
    r"(?i)\bpy\s*spark\b": "data_engineering",
    r"(?i)\bdatabricks\b": "data_engineering",
    r"(?i)\bkafka\b": "data_engineering",
    r"(?i)\bairflow\b": "data_engineering",
    r"(?i)\bkusto\b": "data_engineering",
    r"(?i)\bhadoop\b": "data_engineering",

    # ===== ETL Tools =====
    r"(?i)\btalend\b": "etl_tools",
    r"(?i)\bssis\b": "etl_tools",
    r"(?i)\binformatica\b": "etl_tools",
    r"(?i)\bdata\s*stage\b": "etl_tools",

    # ===== BI Tools / Analytics =====
    r"(?i)\bpower\s*bi\b": "bi_tools",
    r"(?i)\btableau\b": "bi_tools",
    r"(?i)\bqlik\b": "bi_tools",
    r"(?i)\bdax\b": "bi_tools",
    r"(?i)\bssrs\b": "bi_tools",
    r"(?i)\bsas\s*viya\b": "bi_tools",
    r"(?i)\bmicrosoft\s*fabric\b": "bi_tools",
    r"(?i)\btabular\s*model\b": "bi_tools",

    r"(?i)\bpandas\b": "analytics",
    r"(?i)\bnumpy\b": "analytics",
    r"(?i)\bscikit(-|\s*)learn\b": "analytics",

    # ===== Cloud Platforms =====
    r"(?i)\baws\b": "cloud_platforms",
    r"(?i)\bazure(?!\s*(devops|pipelines?|active\s+directory|key\s+vault))\b": "cloud_platforms",
    r"(?i)\bgoogle\s*cloud\b": "cloud_platforms",
    r"(?i)\bgcp\b": "cloud_platforms",
    r"(?i)\bdigital\s*ocean\b": "cloud_platforms",
    r"(?i)\bheroku\b": "cloud_platforms",
    r"(?i)\blinode\b": "cloud_platforms",
    r"(?i)\belastic\s*beanstalk\b": "cloud_platforms",
    r"(?i)\bazure\s+(app\s*services?|functions?)\b": "cloud_platforms",

    # ===== DevOps / IaC =====
    r"(?i)\bterraform\b": "devops_iac",
    r"(?i)\bpulumi\b": "devops_iac",
    r"(?i)\bansible\b": "devops_iac",
    r"(?i)\bcloudformation\b": "devops_iac",
    r"(?i)\barm\s*templates?\b": "devops_iac",
    r"(?i)\bbicep\b": "devops_iac",
    r"(?i)\bvagrant\b": "devops_iac",
    r"(?i)\bmorpheus\b": "devops_iac",

    # ===== CI/CD Tools =====
    r"(?i)\bjenkins\b": "ci_cd_tools",
    r"(?i)\bgitlab\s*(ci/?cd)?\b": "ci_cd_tools",
    r"(?i)\bgithub(\s*actions?)?\b": "ci_cd_tools",
    r"(?i)\bbitbucket(\s*pipelines?)?\b": "ci_cd_tools",
    r"(?i)\bmaven\b": "ci_cd_tools",
    r"(?i)\bnexus\b": "ci_cd_tools",
    r"(?i)\bteamcity\b": "ci_cd_tools",
    r"(?i)\bcircleci\b": "ci_cd_tools",
    r"(?i)\btravis(\s*ci)?\b": "ci_cd_tools",
    r"(?i)\bazure\s*(devops|pipelines?)\b": "ci_cd_tools",

    # ===== Containers & Orchestration =====
    r"(?i)\bdocker(\s*compose)?\b": "containers_orchestration",
    r"(?i)\bkubernetes\b": "containers_orchestration",
    r"(?i)\bhelm\b": "containers_orchestration",
    r"(?i)\bkustomize\b": "containers_orchestration",
    r"(?i)\baks\b": "containers_orchestration",
    r"(?i)\beks\b": "containers_orchestration",
    r"(?i)\bgke\b": "containers_orchestration",
    r"(?i)\bopen\s*shift\b": "containers_orchestration",
    r"(?i)\becs\b": "containers_orchestration",

    # ===== Monitoring & Observability =====
    r"(?i)\bprometheus\b": "monitoring_security",
    r"(?i)\bgrafana\b": "monitoring_security",
    r"(?i)\bdatadog\b": "monitoring_security",
    r"(?i)\bsplunk\b": "monitoring_security",
    r"(?i)\bcloudwatch\b": "monitoring_security",
    r"(?i)\bcloudtrail\b": "monitoring_security",
    r"(?i)\bsentry\b": "monitoring_security",
    r"(?i)\bazure\s+(monitor|application\s+insights|log\s+analytics)\b": "monitoring_security",
    r"(?i)\bapplication\s+insights\b": "monitoring_security",
    r"(?i)\blog\s*analytics\b": "monitoring_security",
    r"(?i)\blogstash\b": "monitoring_security",
    r"(?i)\bkibana\b": "monitoring_security",
    r"(?i)\belk\s*stack\b": "monitoring_security",
    r"(?i)\bcloudtracker\b": "monitoring_security",

    # ===== Security =====
    r"(?i)\biam\b": "security",
    r"(?i)\bwaf\b": "security",
    r"(?i)\bguard(duty)?\b": "security",
    r"(?i)\bsnyk\b": "security",
    r"(?i)\bazure\s+(active\s+directory|key\s+vault)\b": "security",
    r"(?i)\brbac\b": "security",
    r"(?i)\bkeycloak\b": "security",
    r"(?i)\bmacie\b": "security",
    r"(?i)\binspector\b": "security",
    r"(?i)\bsecurity\s+(groups?|monkey|shield)\b": "security",
    r"(?i)\bnacl\b": "security",
    r"(?i)\bshield\b": "security",

    # ===== AI & ML Tools =====
    r"(?i)\bopenai\b": "ai_ml_tools",
    r"(?i)\blangchain\b": "ai_ml_tools",
    r"(?i)\bpytorch\b": "ai_ml_tools",
    r"(?i)\btensorflow\b": "ai_ml_tools",
    r"(?i)\bkeras\b": "ai_ml_tools",
    r"(?i)\bllms?\b": "ai_ml_tools",
    r"(?i)\bwhisper\b": "ai_ml_tools",
    r"(?i)\bllama(index|dex)?\b": "ai_ml_tools",
    r"(?i)\bdeepface\b": "ai_ml_tools",

    # ===== Infrastructure / Operating Systems =====
    r"(?i)\bwindows\s*server\b": "infrastructure_os",
    r"(?i)\blinux\b": "infrastructure_os",
    r"(?i)\bubuntu\b": "infrastructure_os",
    r"(?i)\bred\s*hat\b": "infrastructure_os",
    r"(?i)\bcentos\b": "infrastructure_os",
    r"(?i)\bvmware\b": "infrastructure_os",
    r"(?i)\bhyper[-\s]*v\b": "infrastructure_os",
    r"(?i)\biis\b": "infrastructure_os",

    # ===== Other Tools =====
    r"(?i)\bgit\b": "other_tools",
    r"(?i)\bnginx\b": "other_tools",
    r"(?i)\bapache\b": "other_tools",
}





if __name__ == "__main__":

    # Full technology mapping + PDF output test

    import re
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    from pprint import pprint

