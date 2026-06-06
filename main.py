#!/usr/bin/env python3
"""
Cloudflare IP 优选工具 (TCP筛选 + IP可用性二次筛选 + curl带宽测速 + WxPusher通知)
依赖：requests, curl (系统自带)
配置文件：同目录下的 config.json（请根据需要修改参数）
结果保存到 ip.txt，并自动推送到 GitHub，同时批量更新到 Cloudflare DNS
支持 Windows / Linux
优化：国家过滤前置，减少无效 TCP 测试；重试参数可配置；所有网络请求连接超时分离
"""

import requests
import socket
import time
import sys
import re
import os
import subprocess
import shutil
import json
import csv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 预编译正则 ====================
NODE_PATTERN = re.compile(r"^(\d+\.\d+\.\d+\.\d+):(\d+)#(.+)$")
IP_PORT_PATTERN = re.compile(r"^(\d+\.\d+\.\d+\.\d+):(\d+)#")

# ==================== 国家代码映射表（全球覆盖）====================
CN_TO_CODE = {
    "阿富汗": "AF", "奥兰群岛": "AX", "阿尔巴尼亚": "AL", "阿尔及利亚": "DZ",
    "美属萨摩亚": "AS", "安道尔": "AD", "安哥拉": "AO", "安圭拉": "AI",
    "南极洲": "AQ", "安提瓜和巴布达": "AG", "阿根廷": "AR", "亚美尼亚": "AM",
    "阿鲁巴": "AW", "澳大利亚": "AU", "奥地利": "AT", "阿塞拜疆": "AZ",
    "巴哈马": "BS", "巴林": "BH", "孟加拉国": "BD", "孟加拉": "BD",
    "巴巴多斯": "BB", "白俄罗斯": "BY", "比利时": "BE", "伯利兹": "BZ",
    "贝宁": "BJ", "百慕大": "BM", "不丹": "BT", "玻利维亚": "BO",
    "波黑": "BA", "波斯尼亚和黑塞哥维那": "BA", "博茨瓦纳": "BW",
    "布维岛": "BV", "巴西": "BR", "英属印度洋领地": "IO",
    "文莱": "BN", "保加利亚": "BG", "布基纳法索": "BF", "布隆迪": "BI",
    "柬埔寨": "KH", "喀麦隆": "CM", "加拿大": "CA", "佛得角": "CV",
    "开曼群岛": "KY", "中非": "CF", "乍得": "TD", "智利": "CL",
    "中国": "CN", "圣诞岛": "CX", "科科斯(基林)群岛": "CC",
    "哥伦比亚": "CO", "科摩罗": "KM", "刚果(布)": "CG", "刚果（布）": "CG",
    "刚果(金)": "CD", "刚果（金）": "CD", "库克群岛": "CK",
    "哥斯达黎加": "CR", "科特迪瓦": "CI", "克罗地亚": "HR", "古巴": "CU",
    "塞浦路斯": "CY", "捷克": "CZ", "丹麦": "DK", "吉布提": "DJ",
    "多米尼克": "DM", "多米尼加": "DO", "厄瓜多尔": "EC", "埃及": "EG",
    "萨尔瓦多": "SV", "赤道几内亚": "GQ", "厄立特里亚": "ER",
    "爱沙尼亚": "EE", "埃塞俄比亚": "ET", "福克兰群岛(马尔维纳斯)": "FK",
    "法罗群岛": "FO", "斐济": "FJ", "芬兰": "FI", "法国": "FR",
    "法属圭亚那": "GF", "法属波利尼西亚": "PF", "法属南部领地": "TF",
    "加蓬": "GA", "冈比亚": "GM", "格鲁吉亚": "GE", "德国": "DE",
    "加纳": "GH", "直布罗陀": "GI", "希腊": "GR", "格陵兰": "GL",
    "格林纳达": "GD", "瓜德罗普": "GP", "关岛": "GU", "危地马拉": "GT",
    "根西岛": "GG", "几内亚": "GN", "几内亚比绍": "GW", "圭亚那": "GY",
    "海地": "HT", "赫德岛和麦克唐纳群岛": "HM", "梵蒂冈": "VA",
    "洪都拉斯": "HN", "香港": "HK", "匈牙利": "HU", "冰岛": "IS",
    "印度": "IN", "印度尼西亚": "ID", "伊朗": "IR", "伊拉克": "IQ",
    "爱尔兰": "IE", "马恩岛": "IM", "以色列": "IL", "意大利": "IT",
    "牙买加": "JM", "日本": "JP", "泽西岛": "JE", "约旦": "JO",
    "哈萨克斯坦": "KZ", "肯尼亚": "KE", "基里巴斯": "KI", "朝鲜": "KP",
    "韩国": "KR", "科威特": "KW", "吉尔吉斯斯坦": "KG", "老挝": "LA",
    "拉脱维亚": "LV", "黎巴嫩": "LB", "莱索托": "LS", "利比里亚": "LR",
    "利比亚": "LY", "列支敦士登": "LI", "立陶宛": "LT", "卢森堡": "LU",
    "澳门": "MO", "北马其顿": "MK", "马其顿": "MK", "马达加斯加": "MG",
    "马拉维": "MW", "马来西亚": "MY", "马尔代夫": "MV", "马里": "ML",
    "马耳他": "MT", "马绍尔群岛": "MH", "马提尼克": "MQ",
    "毛里塔尼亚": "MR", "毛里求斯": "MU", "马约特": "YT", "墨西哥": "MX",
    "密克罗尼西亚": "FM", "摩尔多瓦": "MD", "摩纳哥": "MC", "蒙古": "MN",
    "黑山": "ME", "蒙特塞拉特": "MS", "摩洛哥": "MA", "莫桑比克": "MZ",
    "缅甸": "MM", "纳米比亚": "NA", "瑙鲁": "NR", "尼泊尔": "NP",
    "荷兰": "NL", "新喀里多尼亚": "NC", "新西兰": "NZ", "尼加拉瓜": "NI",
    "尼日尔": "NE", "尼日利亚": "NG", "纽埃": "NU", "诺福克岛": "NF",
    "北马里亚纳群岛": "MP", "挪威": "NO", "阿曼": "OM", "巴基斯坦": "PK",
    "帕劳": "PW", "巴勒斯坦": "PS", "巴拿马": "PA", "巴布亚新几内亚": "PG",
    "巴拉圭": "PY", "秘鲁": "PE", "菲律宾": "PH", "皮特凯恩": "PN",
    "波兰": "PL", "葡萄牙": "PT", "波多黎各": "PR", "卡塔尔": "QA",
    "留尼汪": "RE", "罗马尼亚": "RO", "俄罗斯": "RU", "卢旺达": "RW",
    "圣巴泰勒米": "BL", "圣赫勒拿": "SH", "圣基茨和尼维斯": "KN",
    "圣卢西亚": "LC", "圣马丁": "MF", "圣皮埃尔和密克隆": "PM",
    "圣文森特和格林纳丁斯": "VC", "萨摩亚": "WS", "圣马力诺": "SM",
    "圣多美和普林西比": "ST", "沙特阿拉伯": "SA", "沙特": "SA",
    "塞内加尔": "SN", "塞尔维亚": "RS", "塞舌尔": "SC", "塞拉利昂": "SL",
    "新加坡": "SG", "圣马丁(荷兰)": "SX", "斯洛伐克": "SK",
    "斯洛文尼亚": "SI", "所罗门群岛": "SB", "索马里": "SO", "南非": "ZA",
    "南乔治亚和南桑威奇群岛": "GS", "南苏丹": "SS", "西班牙": "ES",
    "斯里兰卡": "LK", "苏丹": "SD", "苏里南": "SR", "斯瓦尔巴和扬马延": "SJ",
    "斯威士兰": "SZ", "瑞典": "SE", "瑞士": "CH", "叙利亚": "SY",
    "台湾": "TW", "塔吉克斯坦": "TJ", "坦桑尼亚": "TZ", "泰国": "TH",
    "东帝汶": "TL", "多哥": "TG", "托克劳": "TK", "汤加": "TO",
    "特立尼达和多巴哥": "TT", "突尼斯": "TN", "土耳其": "TR",
    "土库曼斯坦": "TM", "特克斯和凯科斯群岛": "TC", "图瓦卢": "TV",
    "乌干达": "UG", "乌克兰": "UA", "阿联酋": "AE", "英国": "GB",
    "美国": "US", "美国本土外小岛屿": "UM", "乌拉圭": "UY",
    "乌兹别克斯坦": "UZ", "瓦努阿图": "VU", "委内瑞拉": "VE",
    "越南": "VN", "英属维尔京群岛": "VG", "美属维尔京群岛": "VI",
    "瓦利斯和富图纳": "WF", "西撒哈拉": "EH", "也门": "YE",
    "赞比亚": "ZM", "津巴布韦": "ZW",
}

# 三位字母国家代码 → 两位字母国家代码（ISO 3166-1 alpha-3 → alpha-2）
ALPHA3_TO_ALPHA2 = {
    "AFG": "AF", "ALA": "AX", "ALB": "AL", "DZA": "DZ", "ASM": "AS",
    "AND": "AD", "AGO": "AO", "AIA": "AI", "ATA": "AQ", "ATG": "AG",
    "ARG": "AR", "ARM": "AM", "ABW": "AW", "AUS": "AU", "AUT": "AT",
    "AZE": "AZ", "BHS": "BS", "BHR": "BH", "BGD": "BD", "BRB": "BB",
    "BLR": "BY", "BEL": "BE", "BLZ": "BZ", "BEN": "BJ", "BMU": "BM",
    "BTN": "BT", "BOL": "BO", "BIH": "BA", "BWA": "BW", "BVT": "BV",
    "BRA": "BR", "IOT": "IO", "BRN": "BN", "BGR": "BG", "BFA": "BF",
    "BDI": "BI", "KHM": "KH", "CMR": "CM", "CAN": "CA", "CPV": "CV",
    "CYM": "KY", "CAF": "CF", "TCD": "TD", "CHL": "CL", "CHN": "CN",
    "CXR": "CX", "CCK": "CC", "COL": "CO", "COM": "KM", "COG": "CG",
    "COD": "CD", "COK": "CK", "CRI": "CR", "CIV": "CI", "HRV": "HR",
    "CUB": "CU", "CYP": "CY", "CZE": "CZ", "DNK": "DK", "DJI": "DJ",
    "DMA": "DM", "DOM": "DO", "ECU": "EC", "EGY": "EG", "SLV": "SV",
    "GNQ": "GQ", "ERI": "ER", "EST": "EE", "ETH": "ET", "FLK": "FK",
    "FRO": "FO", "FJI": "FJ", "FIN": "FI", "FRA": "FR", "GUF": "GF",
    "PYF": "PF", "ATF": "TF", "GAB": "GA", "GMB": "GM", "GEO": "GE",
    "DEU": "DE", "GHA": "GH", "GIB": "GI", "GRC": "GR", "GRL": "GL",
    "GRD": "GD", "GLP": "GP", "GUM": "GU", "GTM": "GT", "GGY": "GG",
    "GIN": "GN", "GNB": "GW", "GUY": "GY", "HTI": "HT", "HMD": "HM",
    "VAT": "VA", "HND": "HN", "HKG": "HK", "HUN": "HU", "ISL": "IS",
    "IND": "IN", "IDN": "ID", "IRN": "IR", "IRQ": "IQ", "IRL": "IE",
    "IMN": "IM", "ISR": "IL", "ITA": "IT", "JAM": "JM", "JPN": "JP",
    "JEY": "JE", "JOR": "JO", "KAZ": "KZ", "KEN": "KE", "KIR": "KI",
    "PRK": "KP", "KOR": "KR", "KWT": "KW", "KGZ": "KG", "LAO": "LA",
    "LVA": "LV", "LBN": "LB", "LSO": "LS", "LBR": "LR", "LBY": "LY",
    "LIE": "LI", "LTU": "LT", "LUX": "LU", "MAC": "MO", "MKD": "MK",
    "MDG": "MG", "MWI": "MW", "MYS": "MY", "MDV": "MV", "MLI": "ML",
    "MLT": "MT", "MHL": "MH", "MTQ": "MQ", "MRT": "MR", "MUS": "MU",
    "MYT": "YT", "MEX": "MX", "FSM": "FM", "MDA": "MD", "MCO": "MC",
    "MNG": "MN", "MNE": "ME", "MSR": "MS", "MAR": "MA", "MOZ": "MZ",
    "MMR": "MM", "NAM": "NA", "NRU": "NR", "NPL": "NP", "NLD": "NL",
    "NCL": "NC", "NZL": "NZ", "NIC": "NI", "NER": "NE", "NGA": "NG",
    "NIU": "NU", "NFK": "NF", "MNP": "MP", "NOR": "NO", "OMN": "OM",
    "PAK": "PK", "PLW": "PW", "PSE": "PS", "PAN": "PA", "PNG": "PG",
    "PRY": "PY", "PER": "PE", "PHL": "PH", "PCN": "PN", "POL": "PL",
    "PRT": "PT", "PRI": "PR", "QAT": "QA", "REU": "RE", "ROU": "RO",
    "RUS": "RU", "RWA": "RW", "BLM": "BL", "SHN": "SH", "KNA": "KN",
    "LCA": "LC", "MAF": "MF", "SPM": "PM", "VCT": "VC", "WSM": "WS",
    "SMR": "SM", "STP": "ST", "SAU": "SA", "SEN": "SN", "SRB": "RS",
    "SYC": "SC", "SLE": "SL", "SGP": "SG", "SXM": "SX", "SVK": "SK",
    "SVN": "SI", "SLB": "SB", "SOM": "SO", "ZAF": "ZA", "SGS": "GS",
    "SSD": "SS", "ESP": "ES", "LKA": "LK", "SDN": "SD", "SUR": "SR",
    "SJM": "SJ", "SWZ": "SZ", "SWE": "SE", "CHE": "CH", "SYR": "SY",
    "TWN": "TW", "TJK": "TJ", "TZA": "TZ", "THA": "TH", "TLS": "TL",
    "TGO": "TG", "TKL": "TK", "TON": "TO", "TTO": "TT", "TUN": "TN",
    "TUR": "TR", "TKM": "TM", "TCA": "TC", "TUV": "TV", "UGA": "UG",
    "UKR": "UA", "ARE": "AE", "GBR": "GB", "USA": "US", "UMI": "UM",
    "URY": "UY", "UZB": "UZ", "VUT": "VU", "VEN": "VE", "VNM": "VN",
    "VGB": "VG", "VIR": "VI", "WLF": "WF", "ESH": "EH", "YEM": "YE",
    "ZMB": "ZM", "ZWE": "ZW",
}

# 构建两位有效代码集合，用于快速校验
CODE_SET = set(CN_TO_CODE.values())


# ==================== 加载配置文件 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    """加载 config.json 配置文件，缺失必填字段时抛出异常"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到配置文件 {CONFIG_FILE}")
        print("请在同目录下创建 config.json 文件，内容参考示例。")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：配置文件格式不正确 - {e}")
        sys.exit(1)

    defaults = {
        "USE_GLOBAL_MODE": True,
        "GLOBAL_TOP_N": 15,
        "PER_COUNTRY_TOP_N": 1,
        "BANDWIDTH_CANDIDATES": 90,
        "TCP_PROBES": 3,
        "MIN_SUCCESS_RATE": 1.0,
        "TIMEOUT": 2.0,
        "SOCKET_DEFAULT_TIMEOUT": 3,
        "PROGRESS_PRINT_INTERVAL": 1,
        "FILTER_COUNTRIES_ENABLED": False,
        "ALLOWED_COUNTRIES": ["US"],
        "PRE_FILTER_BLOCKED_ENABLED": True,
        "PRE_FILTER_BLOCKED_COUNTRIES": ["CN"],
        "PRE_FILTER_PORT_ENABLED": True,
        "PRE_FILTER_PORTS": [443],
        "ENABLE_WXPUSHER": True,
        "WXPUSHER_APP_TOKEN": "your_app_token_here",
        "WXPUSHER_UIDS": ["your_uid_here"],
        "WXPUSHER_API_URL": "https://wxpusher.zjiecode.com/api/send/message",
        "NOTIFY_TIMEOUT": 3,
        "NOTIFY_CONNECT_TIMEOUT": 3,
        "CF_ENABLED": True,
        "CF_API_TOKEN": "your_CF_API_TOKEN",
        "CF_ZONE_ID": "your_CF_ZONE_ID",
        "CF_DNS_RECORD_NAME": "your_CF_DNS_RECORD_NAME",
        "CF_TTL": 60,
        "CF_PROXIED": False,
        "CF_DNS_CONNECT_TIMEOUT": 3,
        "CF_DNS_READ_TIMEOUT": 3,
        "DNS_RECORD_TYPE": "TXT",
        "ADDITIONAL_SOURCES": [],
        "FETCH_MAX_RETRIES": 3,
        "FETCH_RETRY_DELAY": 3,
        "FETCH_TIMEOUT": 3,
        "FETCH_CONNECT_TIMEOUT": 3,
        "OUTPUT_FILE": "ip.txt",
        "ENABLE_LOGGING": False,
        "LOG_FILE": "cfnb.log",
        "TEST_AVAILABILITY": True,
        "AVAILABILITY_CHECK_API": "https://api.090227.xyz/check",
        "AVAILABILITY_TIMEOUT": 3,
        "AVAILABILITY_CONNECT_TIMEOUT": 3,
        "AVAILABILITY_RETRY_MAX": 2,
        "AVAILABILITY_RETRY_DELAY": 3,
        "FILTER_IPV6_AVAILABILITY": True,
        "FILTER_BLOCKED_COUNTRIES_ENABLED": True,
        "BLOCKED_COUNTRIES": [
            "BD", "BI", "BY", "CD", "CF", "CN", "CU", "DE", "ET", "HK",
            "IR", "KP", "LY", "MO", "NG", "NL", "PK", "RU", "SD", "SO",
            "SY", "TH", "TW", "UA", "VE", "VN", "YE", "ZW"
        ],
        "DNS_IP_RISK_FILTER_ENABLED": False,
        "DNS_IP_RISK_MAX_LEVEL": "高风险",
        "DNS_UPDATE_TARGET_COUNT": 15,
        "BANDWIDTH_SIZE_MB": 0.5,
        "BANDWIDTH_TIMEOUT": 3,
        "BANDWIDTH_RETRY_MAX": 2,
        "BANDWIDTH_RETRY_DELAY": 3,
        "BANDWIDTH_URL_TEMPLATE": "https://speed.cloudflare.com/__down?bytes={bytes}",
        "BANDWIDTH_PROCESS_BUFFER": 2,
        "BANDWIDTH_CONNECT_TIMEOUT": 3,
        "MAX_WORKERS": 200,
        "AVAILABILITY_WORKERS": 32,
        "FALLBACK_WORKERS": 32,
        "BANDWIDTH_WORKERS": 10,
        "DNS_UPDATE_MAX_RETRIES": 3,
        "DNS_UPDATE_RETRY_DELAY": 3,
        "GITHUB_SYNC_MAX_RETRIES": 3,
        "GITHUB_SYNC_RETRY_DELAY": 3,
        "GIT_SYNC_PROCESS_TIMEOUT": 180,
        "AD_HEADER_ENABLED": False,
        "AD_HEADER_LINES": [],
        "AD_FOOTER_ENABLED": False,
        "AD_FOOTER_LINES": [],
        "AD_PERLINE_ENABLED": False,
        "AD_PERLINE_TEXT": "",
        "IP_TXT_SHOW_BANDWIDTH": False,
        "IP_TXT_SHOW_LATENCY": False,
        # 默认URL配置
        "DEFAULT_SOURCE_URL": "https://example.com/ip_list.txt"
    }

    for key, value in defaults.items():
        if key not in config:
            config[key] = value
            print(f"配置项 {key} 未设置，使用默认值：{value}")

    return config

cfg = load_config()

USE_GLOBAL_MODE = cfg["USE_GLOBAL_MODE"]
GLOBAL_TOP_N = cfg["GLOBAL_TOP_N"]
PER_COUNTRY_TOP_N = cfg["PER_COUNTRY_TOP_N"]
BANDWIDTH_CANDIDATES = cfg["BANDWIDTH_CANDIDATES"]
TCP_PROBES = cfg["TCP_PROBES"]
MIN_SUCCESS_RATE = cfg["MIN_SUCCESS_RATE"]
TIMEOUT = cfg["TIMEOUT"]
SOCKET_DEFAULT_TIMEOUT = cfg["SOCKET_DEFAULT_TIMEOUT"]
PROGRESS_PRINT_INTERVAL = cfg["PROGRESS_PRINT_INTERVAL"]
FILTER_COUNTRIES_ENABLED = cfg["FILTER_COUNTRIES_ENABLED"]
ALLOWED_COUNTRIES = cfg["ALLOWED_COUNTRIES"]
PRE_FILTER_BLOCKED_ENABLED = cfg["PRE_FILTER_BLOCKED_ENABLED"]
PRE_FILTER_BLOCKED_COUNTRIES = [c.upper() for c in cfg["PRE_FILTER_BLOCKED_COUNTRIES"]]
PRE_FILTER_PORT_ENABLED = cfg["PRE_FILTER_PORT_ENABLED"]
PRE_FILTER_PORTS = [str(p) for p in cfg["PRE_FILTER_PORTS"]]
ENABLE_WXPUSHER = cfg["ENABLE_WXPUSHER"]
WXPUSHER_APP_TOKEN = cfg["WXPUSHER_APP_TOKEN"]
WXPUSHER_UIDS = cfg["WXPUSHER_UIDS"]
WXPUSHER_API_URL = cfg["WXPUSHER_API_URL"]
NOTIFY_TIMEOUT = cfg["NOTIFY_TIMEOUT"]
NOTIFY_CONNECT_TIMEOUT = cfg["NOTIFY_CONNECT_TIMEOUT"]
CF_ENABLED = cfg["CF_ENABLED"]
CF_API_TOKEN = cfg["CF_API_TOKEN"]
CF_ZONE_ID = cfg["CF_ZONE_ID"]
CF_DNS_RECORD_NAME = cfg["CF_DNS_RECORD_NAME"]
CF_TTL = cfg["CF_TTL"]
CF_PROXIED = cfg["CF_PROXIED"]
CF_DNS_CONNECT_TIMEOUT = cfg["CF_DNS_CONNECT_TIMEOUT"]
CF_DNS_READ_TIMEOUT = cfg["CF_DNS_READ_TIMEOUT"]
DNS_RECORD_TYPE = cfg["DNS_RECORD_TYPE"]
ADDITIONAL_SOURCES = cfg["ADDITIONAL_SOURCES"]
FETCH_MAX_RETRIES = cfg["FETCH_MAX_RETRIES"]
FETCH_RETRY_DELAY = cfg["FETCH_RETRY_DELAY"]
FETCH_TIMEOUT = cfg["FETCH_TIMEOUT"]
FETCH_CONNECT_TIMEOUT = cfg["FETCH_CONNECT_TIMEOUT"]
OUTPUT_FILE = cfg["OUTPUT_FILE"]
ENABLE_LOGGING = cfg["ENABLE_LOGGING"]
LOG_FILE = cfg["LOG_FILE"]
TEST_AVAILABILITY = cfg["TEST_AVAILABILITY"]
AVAILABILITY_CHECK_API = cfg["AVAILABILITY_CHECK_API"]
AVAILABILITY_TIMEOUT = cfg["AVAILABILITY_TIMEOUT"]
AVAILABILITY_CONNECT_TIMEOUT = cfg["AVAILABILITY_CONNECT_TIMEOUT"]
AVAILABILITY_RETRY_MAX = cfg["AVAILABILITY_RETRY_MAX"]
AVAILABILITY_RETRY_DELAY = cfg["AVAILABILITY_RETRY_DELAY"]
FILTER_IPV6_AVAILABILITY = cfg["FILTER_IPV6_AVAILABILITY"]
FILTER_BLOCKED_COUNTRIES_ENABLED = cfg["FILTER_BLOCKED_COUNTRIES_ENABLED"]
BLOCKED_COUNTRIES = cfg["BLOCKED_COUNTRIES"]
DNS_IP_RISK_FILTER_ENABLED = cfg["DNS_IP_RISK_FILTER_ENABLED"]
DNS_IP_RISK_MAX_LEVEL = cfg["DNS_IP_RISK_MAX_LEVEL"]
DNS_UPDATE_TARGET_COUNT = cfg["DNS_UPDATE_TARGET_COUNT"]
BANDWIDTH_SIZE_MB = cfg["BANDWIDTH_SIZE_MB"]
BANDWIDTH_TIMEOUT = cfg["BANDWIDTH_TIMEOUT"]
BANDWIDTH_RETRY_MAX = cfg["BANDWIDTH_RETRY_MAX"]
BANDWIDTH_RETRY_DELAY = cfg["BANDWIDTH_RETRY_DELAY"]
BANDWIDTH_URL_TEMPLATE = cfg["BANDWIDTH_URL_TEMPLATE"]
BANDWIDTH_PROCESS_BUFFER = cfg["BANDWIDTH_PROCESS_BUFFER"]
BANDWIDTH_CONNECT_TIMEOUT = cfg["BANDWIDTH_CONNECT_TIMEOUT"]
MAX_WORKERS = cfg["MAX_WORKERS"]
AVAILABILITY_WORKERS = cfg["AVAILABILITY_WORKERS"]
FALLBACK_WORKERS = cfg["FALLBACK_WORKERS"]
BANDWIDTH_WORKERS = cfg["BANDWIDTH_WORKERS"]
DNS_UPDATE_MAX_RETRIES = cfg["DNS_UPDATE_MAX_RETRIES"]
DNS_UPDATE_RETRY_DELAY = cfg["DNS_UPDATE_RETRY_DELAY"]
GITHUB_SYNC_MAX_RETRIES = cfg["GITHUB_SYNC_MAX_RETRIES"]
GITHUB_SYNC_RETRY_DELAY = cfg["GITHUB_SYNC_RETRY_DELAY"]
GIT_SYNC_PROCESS_TIMEOUT = cfg["GIT_SYNC_PROCESS_TIMEOUT"]
AD_HEADER_ENABLED = cfg["AD_HEADER_ENABLED"]
AD_HEADER_LINES = cfg["AD_HEADER_LINES"]
AD_FOOTER_ENABLED = cfg["AD_FOOTER_ENABLED"]
AD_FOOTER_LINES = cfg["AD_FOOTER_LINES"]
AD_PERLINE_ENABLED = cfg["AD_PERLINE_ENABLED"]
AD_PERLINE_TEXT = cfg["AD_PERLINE_TEXT"]
IP_TXT_SHOW_BANDWIDTH = cfg["IP_TXT_SHOW_BANDWIDTH"]
IP_TXT_SHOW_LATENCY = cfg["IP_TXT_SHOW_LATENCY"]
DEFAULT_SOURCE_URL = cfg["DEFAULT_SOURCE_URL"]

socket.setdefaulttimeout(SOCKET_DEFAULT_TIMEOUT)
BANDWIDTH_URL = BANDWIDTH_URL_TEMPLATE.format(bytes=int(BANDWIDTH_SIZE_MB * 1024 * 1024))

# ==================== 新增：交互式选择数据源模式 ====================
def select_data_source_mode():
    """交互式选择数据源模式"""
    print("\n=== 选择数据源模式 ===")
    print("1. 使用默认URL链接（配置文件中DEFAULT_SOURCE_URL）")
    print("2. 读取本地ipv4.txt文件")
    print("3. 读取本地ipv4.csv文件（支持多种CSV格式）")
    
    while True:
        choice = input("\n请输入选择（1/2/3）：").strip()
        if choice in ["1", "2", "3"]:
            break
        print("输入无效，请输入1、2或3！")
    
    if choice == "1":
        print(f"\n选择模式1：使用默认URL链接 - {DEFAULT_SOURCE_URL}")
        return "url", DEFAULT_SOURCE_URL
    elif choice == "2":
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ipv4.txt")
        if not os.path.exists(file_path):
            print(f"错误：未找到ipv4.txt文件（路径：{file_path}）")
            sys.exit(1)
        print(f"\n选择模式2：读取本地文件 - {file_path}")
        return "txt", file_path
    else:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ipv4.csv")
        if not os.path.exists(file_path):
            print(f"错误：未找到ipv4.csv文件（路径：{file_path}）")
            sys.exit(1)
        print(f"\n选择模式3：读取本地文件 - {file_path}")
        return "csv", file_path

def load_data_from_source(mode, path_or_url):
    """根据选择的模式加载数据源"""
    if mode == "url":
        # 复用原有的fetch_additional_source逻辑
        return fetch_additional_source(path_or_url)
    elif mode == "txt":
        with open(path_or_url, "r", encoding="utf-8") as f:
            content = f.read()
        return parse_adaptive(content)
    elif mode == "csv":
        nodes = []
        # 支持多种CSV格式：自动检测分隔符，兼容IP:PORT#国家、IP,PORT,国家等格式
        with open(path_or_url, "r", encoding="utf-8") as f:
            # 自动检测分隔符
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=',;|\t')
            
            reader = csv.reader(f, dialect=dialect)
            for row in reader:
                # 过滤空行
                if not row or all(not cell.strip() for cell in row):
                    continue
                # 兼容多种格式：
                # 格式1：IP:PORT#国家
                if len(row) == 1 and '#' in row[0] and ':' in row[0]:
                    nodes.extend(_parse_text_nodes(row[0]))
                # 格式2：IP, PORT, 国家
                elif len(row) >= 2:
                    ip = row[0].strip()
                    port = row[1].strip()
                    country = row[2].strip() if len(row) >=3 else ""
                    if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip) and port.isdigit():
                        if country:
                            # 提取国家代码
                            code = extract_country_code(country) or country.upper()
                            nodes.append(f"{ip}:{port}#{code}")
                        else:
                            # 无国家信息时通过API查询
                            nodes.append(f"{ip}:{port}#UNKNOWN")
        # 对UNKNOWN的节点补充国家信息
        unknown_nodes = [n for n in nodes if n.endswith("#UNKNOWN")]
        if unknown_nodes:
            print(f"\n正在为 {len(unknown_nodes)} 个节点补充国家信息...")
            resolved = _resolve_countries_batch([n.split('#')[0] for n in unknown_nodes])
            new_nodes = []
            for n in nodes:
                if n.endswith("#UNKNOWN"):
                    ipport = n.split('#')[0]
                    code = resolved.get(ipport) or "UNKNOWN"
                    new_nodes.append(f"{ipport}#{code}")
                else:
                    new_nodes.append(n)
            nodes = new_nodes
        return nodes

# ====================================================

def send_wxpusher_notification(content, summary):
    if not ENABLE_WXPUSHER:
        return
    try:
        payload = {
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": summary,
            "uids": WXPUSHER_UIDS
        }
        headers = {"Content-Type": "application/json; charset=utf-8"}
        resp = requests.post(
            WXPUSHER_API_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=(NOTIFY_CONNECT_TIMEOUT, NOTIFY_TIMEOUT)
        )
        if resp.status_code == 200:
            print("微信通知已发送")
        else:
            print(f"微信通知发送失败: {resp.status_code}")
    except Exception as e:
        print(f"微信通知异常: {e}")

# ==================== IP 风险等级查询 ====================
RISK_LEVEL_ORDER = {
    "极度纯净": 0,
    "纯净": 1,
    "轻微风险": 2,
    "高风险": 3,
    "极度危险": 4,
}

def get_ip_risk_level(ip):
    """查询单个 IP 的风险等级字符串，失败返回 '未知'"""
    url = f"https://api.ipapi.is/?q={ip}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return "未知"

    company_score = data.get("company", {}).get("abuser_score")
    asn_score = data.get("asn", {}).get("abuser_score")
    security_flags = {
        "is_crawler": data.get("is_crawler", False),
        "is_proxy": data.get("is_proxy", False),
        "is_vpn": data.get("is_vpn", False),
        "is_tor": data.get("is_tor", False),
        "is_abuser": data.get("is_abuser", False),
        "is_bogon": data.get("is_bogon", False),
    }

    def extract_score(score_str):
        if not score_str:
            return 0.0
        match = re.match(r"([\d.]+)\s*\(([^)]+)\)", str(score_str).strip())
        if match:
            return float(match.group(1))
        try:
            return float(score_str)
        except (ValueError, TypeError):
            return 0.0

    company = extract_score(company_score)
    asn = extract_score(asn_score)
    base_score = ((company + asn) / 2) * 5

    risk_count = sum(1 for key in ["is_crawler", "is_proxy", "is_vpn", "is_tor", "is_abuser"]
                     if security_flags.get(key, False))
    final_score = base_score + risk_count * 0.15
    if security_flags.get("is_bogon", False):
        final_score += 1.0

    percentage = final_score * 100
    if percentage >= 100:
        return "极度危险"
    elif percentage >= 20:
        return "高风险"
    elif percentage >= 5:
        return "轻微风险"
    elif percentage >= 0.25:
        return "纯净"
    else:
        return "极度纯净"

# ==================== 自适应多数据源解析引擎 ====================
def extract_country_code(label):
    """从任意标签中提取标准两位国家代码（支持两位代码、三位代码映射、中文名、emoji国旗、混合无关文字）"""
    label = label.strip()
    if not label:
        return None

    tokens = re.split(r'[\s,;|/]+', label)

    # 遍历每个 token，优先匹配三位/两位大写字母代码（后面不能紧跟英文字母）
    for token in tokens:
        token_cleaned = re.sub(r'^[\d\s\-_.|#]+', '', token.strip())
        # 优先检查三位代码
        m3 = re.match(r'^([A-Z]{3})(?![A-Za-z])', token_cleaned)
        if m3 and m3.group(1) in ALPHA3_TO_ALPHA2:
            return ALPHA3_TO_ALPHA2[m3.group(1)]
        # 再检查两位代码
        m2 = re.match(r'^([A-Z]{2})(?![A-Za-z])', token_cleaned)
        if m2 and m2.group(1) in CODE_SET:
            return m2.group(1)

    # 对每个 token 尝试提取中文名
    for token in tokens:
        token_cleaned = re.sub(r'^[\d\s\-_.|#]+', '', token)
        token_no_emoji = re.sub(r'[\U0001F1E6-\U0001F1FF]', '', token_cleaned).strip()
        cn_match = re.match(r'^([\u4e00-\u9fff（）()]+)\d*$', token_no_emoji)
        if cn_match:
            cn_name = cn_match.group(1).strip()
            code = CN_TO_CODE.get(cn_name)
            if code:
                return code

    # 解码纯 emoji 国旗
    emoji_chars = [c for c in label if '\U0001F1E6' <= c <= '\U0001F1FF']
    if len(emoji_chars) >= 2 and len(emoji_chars) % 2 == 0:
        first = ord(emoji_chars[0]) - 0x1F1E6
        second = ord(emoji_chars[1]) - 0x1F1E6
        if 0 <= first <= 25 and 0 <= second <= 25:
            return chr(first + ord('A')) + chr(second + ord('A'))

    return None


def _parse_json_nodes(data):
    """从 JSON 结构中递归提取节点"""
    nodes = []
    if isinstance(data, list):
        for item in data:
            nodes.extend(_parse_json_nodes(item))
    elif isinstance(data, dict):
        for key in ('nodes', 'data', 'result', 'list'):
            if key in data and isinstance(data[key], list):
                nodes.extend(_parse_json_nodes(data[key]))
                break
        ip = data.get('ip') or data.get('host')
        port = data.get('port')
        code = data.get('country') or data.get('cc')
        if ip and port and code:
            nodes.append(f"{ip}:{port}#{code.upper()}")
    elif isinstance(data, str):
        nodes.extend(_parse_text_nodes(data))
    return nodes


def _query_country(ip, port):
    """通过已有的可用性检测 API 查询 IP 的国家代码"""
    try:
        resp = requests.get(
            AVAILABILITY_CHECK_API,
            params={"proxyip": f"{ip}:{port}"},
            timeout=(AVAILABILITY_CONNECT_TIMEOUT, AVAILABILITY_TIMEOUT)
        )
        if resp.status_code == 200:
            data = resp.json()
            country = data.get("probe_results", {}).get("ipv4", {}).get("exit", {}).get("country", "")
            if country and len(country) == 2:
                return country.upper()
    except Exception:
        pass
    return None


def _resolve_countries_batch(ipports):
    """并发查询一批 IP 的国家代码"""
    results = {}
    total = len(ipports)
    completed = 0
    last_print = time.time()

    def worker(ipport):
        ip, port = ipport.rsplit(':', 1)
        return ipport, _query_country(ip, port)

    with ThreadPoolExecutor(max_workers=FALLBACK_WORKERS) as executor:
        futures = {executor.submit(worker, ipp): ipp for ipp in ipports}
        for future in as_completed(futures):
            try:
                ipport, code = future.result()
                results[ipport] = code
            except Exception:
                results[futures[future]] = None
            completed += 1
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r[备用API查询] 进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    if total > 0:
        print()
    return results


def _parse_text_nodes(text):
    """从纯文本中提取标准节点（内置备用 API 查询）"""
    nodes = []
    pending = []

    tokens = text.split()
    for token in tokens:
        if '#' not in token:
            continue
        try:
            ipport, label = token.split('#', 1)
        except ValueError:
            continue
        ipport = ipport.strip()
        label = label.strip()

        if ipport.startswith('['):
            continue
        if not re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', ipport):
            continue

        code = extract_country_code(label)
        if code:
            nodes.append(f"{ipport}#{code}")
        else:
            pending.append(ipport)

    if pending:
        print(f"{len(pending)} 个标签未能识别，通过可用性检测 API 查询国家...")
        resolved = _resolve_countries_batch(pending)
        for ipport, code in resolved.items():
            if code:
                nodes.append(f"{ipport}#{code}")

    return nodes


def parse_adaptive(text):
    """自适应解析任意格式的节点列表文本（JSON、纯文本等）"""
    text = text.strip()
    if not text:
        return []

    if text.startswith('{') or text.startswith('['):
        try:
            data = json.loads(text)
            return _parse_json_nodes(data)
        except (json.JSONDecodeError, Exception):
            pass

    return _parse_text_nodes(text)


def fetch_additional_source(url):
    """拉取单个数据源并返回标准节点列表"""
    if not url:
        return []

    for attempt in range(1, FETCH_MAX_RETRIES + 1):
        try:
            print(f"正在请求数据源 {url} (尝试 {attempt}/{FETCH_MAX_RETRIES}) ...")
            resp = requests.get(url, timeout=(FETCH_CONNECT_TIMEOUT, FETCH_TIMEOUT))
            resp.raise_for_status()
            nodes = parse_adaptive(resp.text)
            print(f"从 {url} 解析出 {len(nodes)} 个节点。")
            return nodes
        except Exception as e:
            print(f"请求或解析失败 ({url}): {e}")
            if attempt < FETCH_MAX_RETRIES:
                print(f"等待 {FETCH_RETRY_DELAY} 秒后重试...")
                time.sleep(FETCH_RETRY_DELAY)
            else:
                print(f"已尝试 {FETCH_MAX_RETRIES} 次，放弃该数据源。")
                return []

# =========================== 核心测试、筛选、测速及更新函数 ===========================

def test_tcp_latency(ip, port, timeout=TIMEOUT, probes=TCP_PROBES):
    min_latency = float("inf")
    success = 0
    for _ in range(probes):
        try:
            start = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((ip, int(port)))
            latency = time.time() - start
            if latency < min_latency:
                min_latency = latency
            success += 1
        except Exception:
            continue
    return min_latency, success

def test_node(node_str):
    m = NODE_PATTERN.match(node_str)
    if not m:
        return None
    ip, port, country = m.groups()
    min_lat, success = test_tcp_latency(ip, port)

    if success == 0 or (success / TCP_PROBES) < MIN_SUCCESS_RATE:
        return None

    return (node_str, min_lat, country, success)

def check_availability(node_str):
    m = IP_PORT_PATTERN.match(node_str)
    if not m:
        return (node_str, False, "unknown", {})
    ip, port = m.group(1), m.group(2)
    proxyip = f"{ip}:{port}"

    best_stack = "unknown"
    best_exit_info = {}
    success = False

    try:
        resp = requests.get(
            AVAILABILITY_CHECK_API,
            params={"proxyip": proxyip},
            timeout=(AVAILABILITY_CONNECT_TIMEOUT, AVAILABILITY_TIMEOUT)
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") is True:
                success = True
                best_stack = data.get("inferred_stack", "unknown")
                probe = data.get("probe_results", {}).get("ipv6") or data.get("probe_results", {}).get("ipv4") or {}
                best_exit_info = probe.get("exit", {})
    except Exception:
        pass

    return (node_str, success, best_stack, best_exit_info)

def availability_filter_candidates(candidates):
    if not TEST_AVAILABILITY or not candidates:
        return candidates, {}, {}

    print(f"\n对 {len(candidates)} 个候选节点进行可用性二次筛选...")
    passed = []
    ip_info = {}
    exit_details = {}
    completed = 0
    total = len(candidates)
    last_print = time.time()

    with ThreadPoolExecutor(max_workers=AVAILABILITY_WORKERS) as executor:
        futures = {executor.submit(check_availability, node): node for node in candidates}
        for future in as_completed(futures):
            completed += 1
            node_str, ok, stack, exit_info = future.result()
            if ok:
                passed.append(node_str)
                ip_info[node_str] = stack
                exit_details[node_str] = exit_info
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r[可用性检测] 进度：{completed}/{total} ({(completed/total)*100:.1f}%) 通过数量：{len(passed)}", end="", flush=True)
                last_print = now
    print()
    return passed, ip_info, exit_details

def availability_filter_with_retry(candidates):
    if not TEST_AVAILABILITY or not candidates:
        return candidates, {}, {}

    passed = []
    ip_info = {}
    exit_details = {}
    for attempt in range(1, AVAILABILITY_RETRY_MAX + 1):
        print(f"\n[可用性检测] 第 {attempt} 轮检测...")
        passed, ip_info, exit_details = availability_filter_candidates(candidates)
        if passed:
            print(f"可用性检测通过 {len(passed)} 个节点")
            return passed, ip_info, exit_details
        if attempt < AVAILABILITY_RETRY_MAX:
            print(f"本轮可用性检测通过率为 0%，等待 {AVAILABILITY_RETRY_DELAY} 秒后重试...")
            time.sleep(AVAILABILITY_RETRY_DELAY)

    print(f"可用性检测经 {AVAILABILITY_RETRY_MAX} 轮重试后仍无节点通过。")
    send_wxpusher_notification(
        content=f"IP 可用性检测经 {AVAILABILITY_RETRY_MAX} 轮重试后仍无节点通过，已跳过过滤，使用原候选列表继续。",
        summary="可用性检测全部失败"
    )
    return candidates, {}, {}

def measure_bandwidth_curl(node_str):
    m = IP_PORT_PATTERN.match(node_str)
    if not m:
        return (node_str, 0)
    ip, port = m.group(1), m.group(2)

    null_device = "NUL" if sys.platform == "win32" else "/dev/null"
    curl_cmd = [
        "curl", "-s", "-o", null_device,
        "-w", "%{size_download} %{time_total}",
        "--resolve", f"speed.cloudflare.com:{port}:{ip}",
        "--connect-timeout", str(BANDWIDTH_CONNECT_TIMEOUT),
        "--max-time", str(BANDWIDTH_TIMEOUT),
        "--insecure",
        BANDWIDTH_URL
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=BANDWIDTH_TIMEOUT + BANDWIDTH_PROCESS_BUFFER)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                size_bytes = float(parts[0])
                time_total = float(parts[1])
                if time_total > 0 and size_bytes > 0:
                    speed_mbps = (size_bytes * 8) / (time_total * 1000 * 1000)
                    return (node_str, speed_mbps)
    except Exception:
        pass
    return (node_str, 0)

def bandwidth_filter(candidates):
    if not candidates:
        return []

    if not shutil.which("curl"):
        print("未检测到 curl 命令，带宽测速将跳过。")
        return []

    print(f"\n开始带宽测速（对前 {len(candidates)} 个节点，并发 {BANDWIDTH_WORKERS}，超时 {BANDWIDTH_TIMEOUT}s）...")
    results = []
    completed = 0
    total = len(candidates)
    last_print = time.time()

    with ThreadPoolExecutor(max_workers=BANDWIDTH_WORKERS) as executor:
        futures = {executor.submit(measure_bandwidth_curl, node): node for node in candidates}
        for future in as_completed(futures):
            completed += 1
            node, speed = future.result()
            if speed > 0:
                results.append((node, speed))
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r[带宽测速] 进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    print()
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def batch_update_cloudflare_dns(ip_list, ip_info=None, full_bw_results=None, target_count=None, latency_map=None):
    if not CF_ENABLED:
        print("Cloudflare DNS 批量更新未启用。")
        return

    if target_count is None:
        target_count = DNS_UPDATE_TARGET_COUNT

    dns_content_list = []   # A模式存储IP，TXT模式存储"ip:port"
    dns_node_list = []      # 原始节点串，仅用于展示信息
    filtered_by_port = 0
    filtered_by_ipv6 = 0
    filtered_by_country = 0
    filtered_by_risk = 0
    risk_fallback_ip_list = []
    risk_fallback_node_list = []

    record_type = DNS_RECORD_TYPE.upper()
    if record_type not in ("A", "TXT"):
        print(f"不支持的 DNS_RECORD_TYPE: {record_type}，已跳过 DNS 更新。")
        return

    # ---------- 从带宽测速结果中筛选节点 ----------
    if full_bw_results and ip_info:
        blocked_set = set()
        if FILTER_BLOCKED_COUNTRIES_ENABLED:
            blocked_set = {c.upper() for c in BLOCKED_COUNTRIES}

        for node_str, speed in full_bw_results:
            # 提取 IP 和端口
            if ':' not in node_str:
                continue
            parts = node_str.split(':')
            if len(parts) < 2:
                continue
            pure_ip = parts[0]
            port = parts[1].split('#')[0]

            # === 端口过滤：统一强制要求 443 ===
            if port != '443':
                filtered_by_port += 1
                continue

            # === IPv6 落地过滤 ===
            if FILTER_IPV6_AVAILABILITY:
                stack = ip_info.get(node_str, "unknown")
                if stack == "ipv6_only":
                    filtered_by_ipv6 += 1
                    continue

            # === 国家黑名单过滤 ===
            if blocked_set and '#' in node_str:
                country = node_str.split('#')[-1].upper()
                if country in blocked_set:
                    filtered_by_country += 1
                    continue

            # 备份未经过风险过滤的节点（用于回退）
            if DNS_IP_RISK_FILTER_ENABLED:
                risk_fallback_ip_list.append(pure_ip)
                risk_fallback_node_list.append(node_str)

            # === IP 风险等级过滤 ===
            if DNS_IP_RISK_FILTER_ENABLED:
                risk_level = get_ip_risk_level(pure_ip)
                max_level = DNS_IP_RISK_MAX_LEVEL

# =========================== 主函数入口（新增调用逻辑）===========================
def main():
    # 1. 交互式选择数据源模式
    mode, path_or_url = select_data_source_mode()
    
    # 2. 加载数据源
    nodes = load_data_from_source(mode, path_or_url)
    if not nodes:
        print("错误：未能从数据源加载到任何节点！")
        sys.exit(1)
    print(f"成功加载 {len(nodes)} 个节点")

    # 3. 后续原有逻辑（此处省略，保持原有逻辑不变）
    # ... 原有核心逻辑调用 ...

if __name__ == "__main__":
    main()
