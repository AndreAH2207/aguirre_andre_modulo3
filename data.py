from case_config import PARAMETERS

PRODUCTS={
    "KRN-900X":{"sku":"KRN-900X","name":"Edge AI Computer KRONOS-Edge AI-900X","category":"Edge Computing","price_usd":2450.50},
    "NXS-G10":{"sku":"NXS-G10","name":"Industrial Gateway NEXUS-Gateway Lite-G10","category":"Edge Computing","price_usd":685.25},
    "OPT-V300":{"sku":"OPT-V300","name":"Smart Camera OPTIX-SmartCam V300","category":"Computer Vision","price_usd":1575.80},
    "CYC-3DX":{"sku":"CYC-3DX","name":"3D Laser Scanner CYCLOP-3D Profiler-X","category":"Computer Vision","price_usd":4120.45},
    "TTN-M40":{"sku":"TTN-M40","name":"PLC Controller TITAN-PLC Core-M40","category":"Automation","price_usd":3210.60},
}
STOCK={"KRN-900X":45,"NXS-G10":120,"OPT-V300":62,"CYC-3DX":14,"TTN-M40":35}

CUSTOMERS={
    "C-1003":{"customer_id":"C-1003","name":"Robotics Lab Chile","credit_status":"ok","credit_limit_usd":PARAMETERS["credit_limit_usd"],"current_exposure_usd":PARAMETERS["current_exposure_usd"]},
    "C-1010":{"customer_id":"C-1010","name":"Altiplano Mining Automation","credit_status":"ok","credit_limit_usd":120000,"current_exposure_usd":20000},
    "C-9999":{"customer_id":"C-9999","name":"Blocked Customer","credit_status":"hold","credit_limit_usd":50000,"current_exposure_usd":35000},
}
REVIEW_AMOUNT_USD=PARAMETERS["review_amount_usd"]
