#!/usr/bin/env python3
"""
Cloudflare IP 优选工具 (TCP筛选 + IP可用性二次筛选 + HTTP检测 + curl带宽测速 + WxPusher通知)
依赖：requests, curl (系统自带)
配置文件：同目录下的 config.json（请根据需要修改参数）
结果保存到 ip.txt，并自动推送到 GitHub，同时批量更新到 Cloudflare DNS
支持 Windows / Linux / Termux

【新增】终端交互式菜单：支持手动选择 URL优选、本地TXT、本地CSV 模式
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
from urllib3.exceptions import InsecureRequestWarning

# 禁用 SSL 警告 (用于 HTTP 检测)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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
    "圣护西亚": "LC", "圣马丁": "MF", "圣皮埃尔和密克隆": "PM",
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
        "HTTP_TEST_ENABLED": True,
        "HTTP_TEST_TIMEOUT": 3,
        "HTTP_TEST_MAX_RETRIES": 2,
        "HTTP_TEST_RETRY_DELAY": 3,
        "HTTP_TEST_WORKERS": 32,
        "HTTP_TEST_METHOD": "HEAD",
        "HTTP_TEST_MAX_ROUNDS": 2,
        "HTTP_TEST_ROUND_DELAY": 3,
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
HTTP_TEST_ENABLED = cfg["HTTP_TEST_ENABLED"]
HTTP_TEST_TIMEOUT = cfg["HTTP_TEST_TIMEOUT"]
HTTP_TEST_MAX_RETRIES = cfg["HTTP_TEST_MAX_RETRIES"]
HTTP_TEST_RETRY_DELAY = cfg["HTTP_TEST_RETRY_DELAY"]
HTTP_TEST_WORKERS = cfg["HTTP_TEST_WORKERS"]
HTTP_TEST_METHOD = cfg["HTTP_TEST_METHOD"]
HTTP_TEST_MAX_ROUNDS = cfg["HTTP_TEST_MAX_ROUNDS"]
HTTP_TEST_ROUND_DELAY = cfg["HTTP_TEST_ROUND_DELAY"]
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

socket.setdefaulttimeout(SOCKET_DEFAULT_TIMEOUT)
BANDWIDTH_URL = BANDWIDTH_URL_TEMPLATE.format(bytes=int(BANDWIDTH_SIZE_MB * 1024 * 1024))

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
    if not label:
        return None
    label = str(label).strip()
    if not label:
        return None

    tokens = re.split(r'[\s,;|/]+', label)

    for token in tokens:
        token_cleaned = re.sub(r'^[\d\s\-_.|#]+', '', token.strip())
        m3 = re.match(r'^([A-Z]{3})(?![A-Za-z])', token_cleaned)
        if m3 and m3.group(1) in ALPHA3_TO_ALPHA2:
            return ALPHA3_TO_ALPHA2[m3.group(1)]
        m2 = re.match(r'^([A-Z]{2})(?![A-Za-z])', token_cleaned)
        if m2 and m2.group(1) in CODE_SET:
            return m2.group(1)

    for token in tokens:
        token_cleaned = re.sub(r'^[\d\s\-_.|#]+', '', token)
        token_no_emoji = re.sub(r'[\U0001F1E6-\U0001F1FF]', '', token_cleaned).strip()
        cn_match = re.match(r'^([\u4e00-\u9fff（）()]+)\d*$', token_no_emoji)
        if cn_match:
            cn_name = cn_match.group(1).strip()
            code = CN_TO_CODE.get(cn_name)
            if code:
                return code

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


def parse_csv_adaptive(file_path):
    """自适应解析本地各类型 CSV 表格，通过模糊匹配探测 IP、端口、国家位置"""
    nodes = []
    if not os.path.exists(file_path):
        return nodes

    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            sample = f.read(2048)
            f.seek(0)
            if not sample.strip():
                return nodes
            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(f, dialect)
            except Exception:
                reader = csv.reader(f)

            rows = list(reader)

        if not rows:
            return nodes

        header = [str(cell).strip().lower() for cell in rows[0]]
        ip_idx, port_idx, country_idx = -1, -1, -1

        ip_keywords = ['ip', 'addr', 'host', '地址', '节点']
        port_keywords = ['port', '端口']
        country_keywords = ['country', 'cc', '国家', '地区', '位置', '描述', '标签', 'label']

        for i, col in enumerate(header):
            if any(k in col for k in ip_keywords) and ip_idx == -1:
                ip_idx = i
            elif any(k in col for k in port_keywords) and port_idx == -1:
                port_idx = i
            elif any(k in col for k in country_keywords) and country_idx == -1:
                country_idx = i

        if ip_idx == -1:
            ip_idx = 0
            if len(header) > 1: port_idx = 1
            if len(header) > 2: country_idx = 2

        pending_ips = []
        for row in rows[1:]:
            if not row or len(row) <= ip_idx:
                continue
            
            ip = str(row[ip_idx]).strip()
            if ':' in ip:
                ip_parts = ip.split(':')
                ip = ip_parts[0].strip()
                port = ip_parts[1].strip()
            else:
                port = str(row[port_idx]).strip() if (port_idx != -1 and len(row) > port_idx) else "443"

            if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                continue
            if not port.isdigit():
                port = "443"

            label = str(row[country_idx]).strip() if (country_idx != -1 and len(row) > country_idx) else "US"
            code = extract_country_code(label)

            if code:
                nodes.append(f"{ip}:{port}#{code}")
            else:
                pending_ips.append(f"{ip}:{port}")

        if pending_ips:
            print(f"[CSV解析] 有 {len(pending_ips)} 个节点未提取到有效国家代码，启动 API 异步补全...")
            resolved = _resolve_countries_batch(pending_ips)
            for ipport, code in resolved.items():
                if code:
                    nodes.append(f"{ipport}#{code}")
                else:
                    nodes.append(f"{ipport}#US")

    except Exception as e:
        print(f"解析本地 CSV 文件异常: {e}")

    return nodes


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

def check_http_server(node_str, timeout, max_retries, retry_delay, method):
    m = IP_PORT_PATTERN.match(node_str)
    if not m:
        return (node_str, False, "parse_error")
    ip, port = m.group(1), m.group(2)
    url = f"http://{ip}:{port}/cdn-cgi/trace"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "HEAD":
                resp = requests.head(url, timeout=timeout, verify=False, allow_redirects=False, headers=headers)
            else:
                resp = requests.get(url, timeout=timeout, verify=False, allow_redirects=False, headers=headers)
            if resp.status_code != 400:
                return (node_str, False, f"status_{resp.status_code}")
            server = resp.headers.get("server", "")
            if server.lower().startswith("cloudflare"):
                return (node_str, True, server)
            else:
                return (node_str, False, server)
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            else:
                return (node_str, False, "timeout")
        except Exception:
            return (node_str, False, "connection_error")

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

def http_server_filter(candidates, config):
    """并发 HTTP 检测，支持整体失败重试，全部失败时降级并通知"""
    if not config.get("HTTP_TEST_ENABLED", False) or not candidates:
        return candidates

    timeout = HTTP_TEST_TIMEOUT
    max_retries = HTTP_TEST_MAX_RETRIES
    retry_delay = HTTP_TEST_RETRY_DELAY
    workers = HTTP_TEST_WORKERS
    method = HTTP_TEST_METHOD
    max_rounds = HTTP_TEST_MAX_ROUNDS
    round_delay = HTTP_TEST_ROUND_DELAY

    for round_num in range(1, max_rounds + 1):
        print(f"\n[HTTP检测] 第 {round_num} 轮检测...")
        print(f"\n对 {len(candidates)} 个候选节点进行 HTTP 二次筛选...")

        passed = []
        total = len(candidates)
        completed = 0
        last_print = time.time()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(check_http_server, node, timeout, max_retries, retry_delay, method): node
                for node in candidates
            }
            for future in as_completed(future_map):
                node_str, valid, server = future.result()
                completed += 1
                if valid:
                    passed.append(node_str)
                now = time.time()
                if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                    print(f"\r[HTTP检测] 进度：{completed}/{total} ({(completed/total)*100:.1f}%) 通过数量：{len(passed)}", end="", flush=True)
                    last_print = now

        print()
        if passed:
            print(f"HTTP检测通过 {len(passed)} 个节点")
            return passed
        elif round_num < max_rounds:
            print(f"本轮 HTTP 检测通过率为 0%，等待 {round_delay} 秒后重试...")
            time.sleep(round_delay)

    # 全部轮次失败，降级
    send_wxpusher_notification(
        content=f"HTTP检测经 {max_rounds} 轮重试后仍无节点通过，已降级使用过滤前列表。",
        summary="HTTP检测全部失败"
    )
    print(f"HTTP检测经 {max_rounds} 轮重试后仍无节点通过，降级使用过滤前候选列表。")
    return candidates

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

    dns_content_list = []   
    dns_node_list = []      
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

    if full_bw_results and ip_info:
        blocked_set = set()
        if FILTER_BLOCKED_COUNTRIES_ENABLED:
            blocked_set = {c.upper() for c in BLOCKED_COUNTRIES}

        for node_str, speed in full_bw_results:
            if ':' not in node_str:
                continue
            parts = node_str.split(':')
            if len(parts) < 2:
                continue
            pure_ip = parts[0]
            port = parts[1].split('#')[0]

            if port != '443':
                filtered_by_port += 1
                continue

            if FILTER_IPV6_AVAILABILITY:
                stack = ip_info.get(node_str, "unknown")
                if stack == "ipv6_only":
                    filtered_by_ipv6 += 1
                    continue

            if blocked_set and '#' in node_str:
                country = node_str.split('#')[-1].upper()
                if country in blocked_set:
                    filtered_by_country += 1
                    continue

            if DNS_IP_RISK_FILTER_ENABLED:
                risk_fallback_ip_list.append(pure_ip)
                risk_fallback_node_list.append(node_str)

            if DNS_IP_RISK_FILTER_ENABLED:
                risk_level = get_ip_risk_level(pure_ip)
                max_level = DNS_IP_RISK_MAX_LEVEL
                if risk_level == "未知" or RISK_LEVEL_ORDER.get(risk_level, 99) > RISK_LEVEL_ORDER.get(max_level, 2):
                    filtered_by_risk += 1
                    continue

            if record_type == "A":
                dns_content_list.append(pure_ip)
            else:   
                dns_content_list.append(f"{pure_ip}:{port}")
            dns_node_list.append(node_str)

            if len(dns_content_list) >= target_count:
                break

        if DNS_IP_RISK_FILTER_ENABLED and not dns_content_list and filtered_by_risk > 0:
            send_wxpusher_notification(
                content="风险等级检测全部失败：所有候选节点均因风险等级过高或 API 查询失败被过滤，已回退到无风险等级过滤的候选列表。",
                summary="风险等级检测全部失败"
            )
            fallback_content = []
            fallback_nodes = []
            for i, (ip, node) in enumerate(zip(risk_fallback_ip_list, risk_fallback_node_list)):
                if record_type == "A":
                    fallback_content.append(ip)
                else:
                    ip_port = node.split('#')[0]
                    fallback_content.append(ip_port)
                fallback_nodes.append(node)
                if len(fallback_content) >= target_count:
                    break
            dns_content_list = fallback_content
            dns_node_list = fallback_nodes

        filter_parts = []
        if filtered_by_port > 0:
            filter_parts.append(f"非443端口过滤({filtered_by_port}个)")
        if FILTER_IPV6_AVAILABILITY:
            filter_parts.append(f"IPv6落地过滤({filtered_by_ipv6}个)")
        if FILTER_BLOCKED_COUNTRIES_ENABLED:
            filter_parts.append(f"DNS黑名单过滤({filtered_by_country}个)")
        if DNS_IP_RISK_FILTER_ENABLED and filtered_by_risk > 0:
            filter_parts.append(f"风险等级过滤({filtered_by_risk}个)")
        filter_str = " + ".join(filter_parts) if filter_parts else "无过滤"
        print(f"从 {len(full_bw_results)} 个测速节点中筛选出 {len(dns_content_list)} 个{'IP' if record_type=='A' else 'IP:端口'} 用于 DNS 更新（{filter_str}）。")

    if not dns_content_list:
        if ip_list:
            print("未能从完整测速结果构建 DNS 列表，降级使用 ip.txt 中的 IP。")
            if record_type == "A":
                dns_content_list = ip_list
                dns_node_list = ip_list
            else:
                print("TXT 模式需要端口信息，但降级数据中无端口，DNS 更新跳过。")
                return
        else:
            msg = "没有可用的 IP 用于 DNS 更新，跳过。"
            print(msg)
            send_wxpusher_notification(content=msg, summary="DNS 更新跳过")
            return

    seen = set()
    unique_content = []
    unique_nodes = []
    for content, node in zip(dns_content_list, dns_node_list):
        if content not in seen:
            seen.add(content)
            unique_content.append(content)
            unique_nodes.append(node)
    dns_content_list = unique_content
    dns_node_list = unique_nodes

    print(f"\n准备将以下 {len(dns_content_list)} 个{'IP' if record_type=='A' else 'IP:端口'} 更新到 Cloudflare DNS（记录类型 {record_type}）:")
    speed_map = {}
    if full_bw_results:
        speed_map = {node: speed for node, speed in full_bw_results}
    for i, (content, node) in enumerate(zip(dns_content_list, dns_node_list), 1):
        speed = speed_map.get(node, 0)
        lat_ms = float('inf')
        if latency_map and node in latency_map:
            lat_ms = latency_map[node] * 1000
        if lat_ms != float('inf'):
            print(f"{i}. {content} 速度 {speed:.2f} Mbps 延迟 {lat_ms:.2f} ms")
        else:
            print(f"{i}. {content} 速度 {speed:.2f} Mbps")

    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    if record_type == "A":
        for attempt in range(1, DNS_UPDATE_MAX_RETRIES + 1):
            print(f"\n[DNS 更新] 尝试 {attempt}/{DNS_UPDATE_MAX_RETRIES}...")
            try:
                list_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records?type=A&name={CF_DNS_RECORD_NAME}"
                response = requests.get(list_url, headers=headers, timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
                response.raise_for_status()
                result = response.json()
                if not result.get('success'):
                    raise Exception(f"查询 DNS 记录失败: {result.get('errors')}")

                existing_records = result.get('result', [])
                deletes = [{"id": rec["id"]} for rec in existing_records]
                posts = [
                    {
                        "name": CF_DNS_RECORD_NAME,
                        "type": "A",
                        "content": ip,
                        "ttl": CF_TTL,
                        "proxied": CF_PROXIED
                    }
                    for ip in dns_content_list
                ]

                batch_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/batch"
                payload = {"deletes": deletes, "posts": posts}
                response = requests.post(batch_url, headers=headers, json=payload,
                                        timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
                response.raise_for_status()
                result = response.json()
                if not result.get('success'):
                    raise Exception(f"批量更新失败: {result.get('errors')}")

                success_msg = f"Cloudflare DNS 批量更新成功！已将 {CF_DNS_RECORD_NAME} 指向 {len(dns_content_list)} 个 IP。"
                print(success_msg)
                print("注意：DNS 解析将随机返回这些 IP 中的一个，实现负载均衡。")
                return

            except Exception as e:
                error_msg = f"[尝试 {attempt}/{DNS_UPDATE_MAX_RETRIES}] DNS 更新出错: {e}"
                print(error_msg)
                if attempt < DNS_UPDATE_MAX_RETRIES:
                    print(f"等待 {DNS_UPDATE_RETRY_DELAY} 秒后重试...")
                    time.sleep(DNS_UPDATE_RETRY_DELAY)
                else:
                    final_error = f"Cloudflare DNS 更新失败，已重试 {DNS_UPDATE_MAX_RETRIES} 次，错误：{e}"
                    print(final_error)
                    send_wxpusher_notification(content=final_error, summary="DNS 更新失败")

    else:   
        for attempt in range(1, DNS_UPDATE_MAX_RETRIES + 1):
            print(f"\n[TXT 记录更新] 尝试 {attempt}/{DNS_UPDATE_MAX_RETRIES}...")
            try:
                list_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records?type=TXT&name={CF_DNS_RECORD_NAME}"
                resp = requests.get(list_url, headers=headers, timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
                resp.raise_for_status()
                existing = resp.json().get('result', [])
                deletes = [{"id": rec["id"]} for rec in existing]

                posts = [
                    {
                        "name": CF_DNS_RECORD_NAME,
                        "type": "TXT",
                        "content": content,
                        "ttl": CF_TTL
                    }
                    for content in dns_content_list
                ]

                batch_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/batch"
                payload = {"deletes": deletes, "posts": posts}
                batch_resp = requests.post(batch_url, headers=headers, json=payload,
                                           timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
                batch_resp.raise_for_status()
                result = batch_resp.json()
                if not result.get('success'):
                    raise Exception(f"批量更新失败: {result.get('errors')}")

                print(f"Cloudflare TXT 记录批量更新成功！共 {len(dns_content_list)} 条记录，每条内容为一个 IP:端口。")
                return

            except Exception as e:
                error_msg = f"[尝试 {attempt}/{DNS_UPDATE_MAX_RETRIES}] TXT 更新出错: {e}"
                print(error_msg)
                if attempt < DNS_UPDATE_MAX_RETRIES:
                    print(f"等待 {DNS_UPDATE_RETRY_DELAY} 秒后重试...")
                    time.sleep(DNS_UPDATE_RETRY_DELAY)
                else:
                    final_error = f"Cloudflare TXT 记录更新失败，已重试 {DNS_UPDATE_MAX_RETRIES} 次，错误：{e}"
                    print(final_error)
                    send_wxpusher_notification(content=final_error, summary="DNS 更新失败")

def sync_to_github():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if sys.platform == "win32":
        script_name = "git_sync.ps1"
        interpreter = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]
        creationflags = subprocess.CREATE_NO_WINDOW
    else:
        script_name = "git_sync.sh"
        interpreter = ["bash"]
        creationflags = 0

    script_path = os.path.join(script_dir, script_name)
    if not os.path.exists(script_path):
        print(f"未找到 {script_name}，跳过 GitHub 同步。")
        return

    if sys.platform != "win32":
        try:
            os.chmod(script_path, 0o755)
        except Exception:
            pass

    for attempt in range(1, GITHUB_SYNC_MAX_RETRIES + 1):
        print(f"\n正在同步到 GitHub (尝试 {attempt}/{GITHUB_SYNC_MAX_RETRIES})...")
        try:
            cmd = interpreter + [script_path]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags
            )

            try:
                stdout, stderr = process.communicate(timeout=GIT_SYNC_PROCESS_TIMEOUT)
                if process.returncode == 0:
                    print("已自动推送到 GitHub。")
                    return
                else:
                    print(f"推送失败 (退出码 {process.returncode})")
                    if stderr:
                        print(f"错误信息: {stderr.strip()}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"推送超时（超过 {GIT_SYNC_PROCESS_TIMEOUT} 秒）")
        except Exception as e:
            print(f"推送过程异常: {e}")

        if attempt < GITHUB_SYNC_MAX_RETRIES:
            print(f"等待 {GITHUB_SYNC_RETRY_DELAY} 秒后重试...")
            time.sleep(GITHUB_SYNC_RETRY_DELAY)

    send_wxpusher_notification(
        content=f"GitHub 推送失败，已重试 {GITHUB_SYNC_MAX_RETRIES} 次，请检查网络或仓库状态。",
        summary="GitHub 推送失败"
    )
    print(f"已尝试 {GITHUB_SYNC_MAX_RETRIES} 次推送，均失败，请检查网络或 GitHub 仓库状态。")

def write_ip_txt(final_nodes, output_file,
                 header_enabled, header_lines,
                 footer_enabled, footer_lines,
                 perline_enabled, perline_text,
                 speed_map=None, latency_map=None):
    """生成包含广告的 ip.txt"""
    with open(output_file, "w", encoding="utf-8") as f:
        if header_enabled:
            for line in header_lines:
                f.write(line + "\n")
        for node in final_nodes:
            line = node
            if IP_TXT_SHOW_BANDWIDTH and speed_map and node in speed_map:
                line += f" {speed_map[node]:.2f} Mbps"
            if IP_TXT_SHOW_LATENCY and latency_map and node in latency_map:
                line += f" {latency_map[node]*1000:.2f} ms"
            if perline_enabled and perline_text:
                line += perline_text
            f.write(line + "\n")
        if footer_enabled:
            for line in footer_lines:
                f.write(line + "\n")

def show_interactive_menu():
    """在终端渲染出漂亮的交互式选择菜单，支持单选或组合多选模式"""
    print("\n" + "="*45)
    print("      Cloudflare IP 优选工具 - 数据源选择")
    print("="*45)
    print(" 1. 模式一：仅加载 远程 URL 订阅优选")
    print(" 2. 模式二：仅加载 本地 ipv4.txt 优选")
    print(" 3. 模式三：仅加载 本地 ipv4.csv 优选")
    print(" 4. 模式四：全加载 (URL + ipv4.txt + ipv4.csv)")
    print(" 5. 自定义：手动组合 (例如输入 1,2 或 2,3)")
    print(" 0. 退出程序")
    print("="*45)
    
    while True:
        try:
            choice = input("👉 请输入您的选择并按回车: ").strip()
            if choice == '0':
                print("已安全退出程序。")
                sys.exit(0)
            elif choice == '1':
                return [1]
            elif choice == '2':
                return [2]
            elif choice == '3':
                return [3]
            elif choice == '4':
                return [1, 2, 3]
            elif choice == '5':
                custom_input = input("👉 请输入要组合的模式编号（用逗号隔开，如 1,2）: ").strip()
                selected = []
                for x in custom_input.split(','):
                    x = x.strip()
                    if x in ['1', '2', '3']:
                        selected.append(int(x))
                if selected:
                    return list(set(selected))
                else:
                    print("⚠️ 输入无效，请重新选择组合。")
            else:
                print("⚠️ 输入有误，请输入 0-5 之间的有效指令。")
        except (KeyboardInterrupt, EOFError):
            print("\n已强行终止。")
            sys.exit(0)

def main():
    mode_str = f"全局最优{GLOBAL_TOP_N}个" if USE_GLOBAL_MODE else f"每个国家最优{PER_COUNTRY_TOP_N}个"
    print(f"当前模式：{mode_str}，每个节点测试 {TCP_PROBES} 次 TCP 连接")
    print(f"最低成功率要求：{MIN_SUCCESS_RATE*100:.0f}%")
    print(f"IP 可用性二次筛选：{'启用' if TEST_AVAILABILITY else '禁用'}（仅对候选节点）")
    print(f"HTTP检测：{'启用' if HTTP_TEST_ENABLED else '禁用'}（仅对候选节点）")
    print(f"IPv6 客户端 IP 过滤（仅作用于DNS更新环节）：{'启用' if FILTER_IPV6_AVAILABILITY else '禁用'}")
    print(f"DNS黑名单过滤：{'启用' if FILTER_BLOCKED_COUNTRIES_ENABLED else '禁用'}，黑名单国家：{', '.join(BLOCKED_COUNTRIES)}")
    print(f"IP 风险等级过滤：{'启用' if DNS_IP_RISK_FILTER_ENABLED else '禁用'}（最高允许：{DNS_IP_RISK_MAX_LEVEL}）")
    print(f"带宽测速候选数：{BANDWIDTH_CANDIDATES}，测速文件大小：{BANDWIDTH_SIZE_MB} MB，超时：{BANDWIDTH_TIMEOUT}s")
    if FILTER_COUNTRIES_ENABLED:
        print(f"前置白名单过滤：启用，仅保留：{', '.join(ALLOWED_COUNTRIES)}")

    # 调用终端交互菜单获取用户选定的模式列表
    selected_modes = show_interactive_menu()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    nodes = []

    # ==================== 模式一：URL 优选远程加载 ====================
    if 1 in selected_modes:
        if ADDITIONAL_SOURCES:
            print("\n[数据源：远程URL] 开始加载远程订阅列表...")
            for source in ADDITIONAL_SOURCES:
                if not source.get("enabled", True):
                    continue
                url = source.get("url")
                if not url:
                    continue
                v2_nodes = fetch_additional_source(url)
                if v2_nodes:
                    nodes.extend(v2_nodes)
        else:
            print("\n⚠️ 提示：您选了模式一，但在 config.json 的 ADDITIONAL_SOURCES 中未配置任何远程 URL。")

    # ==================== 模式二：本地 ipv4.txt 加载 ====================
    if 2 in selected_modes:
        txt_file_path = os.path.join(script_dir, "ipv4.txt")
        if os.path.exists(txt_file_path):
            print("\n[数据源：本地TXT] 检测到 ipv4.txt，开始自适应解析...")
            try:
                with open(txt_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    txt_content = f.read()
                    txt_nodes = parse_adaptive(txt_content)
                    print(f"从 ipv4.txt 加载并解析出 {len(txt_nodes)} 个节点。")
                    nodes.extend(txt_nodes)
            except Exception as e:
                print(f"读取本地 ipv4.txt 失败: {e}")
        else:
            print(f"\n⚠️ 错误：未在目录下找到本地 {txt_file_path} 文件，跳过此加载项。")

    # ==================== 模式三：本地 ipv4.csv 加载 ====================
    if 3 in selected_modes:
        csv_file_path = os.path.join(script_dir, "ipv4.csv")
        if os.path.exists(csv_file_path):
            print("\n[数据源：本地CSV] 检测到 ipv4.csv，进入全格式自适应识别匹配...")
            csv_nodes = parse_csv_adaptive(csv_file_path)
            print(f"从 ipv4.csv 加载并智能过滤出 {len(csv_nodes)} 个可用节点。")
            nodes.extend(csv_nodes)
        else:
            print(f"\n⚠️ 错误：未在目录下找到本地 {csv_file_path} 文件，跳过此加载项。")

    # ==================== 全局节点提纯与去重 ====================
    if nodes:
        seen = set()
        unique_nodes = []
        for n in nodes:
            key = n.split('#')[0]
            if key not in seen:
                seen.add(key)
                unique_nodes.append(n)
        nodes = unique_nodes
    
    print(f"\n================ 您选定的数据源合并去重后，总计 {len(nodes)} 个节点进入清洗过滤段 ================")

    if not nodes:
        print("没有获取到任何有效节点，退出。")
        sys.exit(1)

    # 前置端口过滤
    if PRE_FILTER_PORT_ENABLED:
        before = len(nodes)
        nodes = [n for n in nodes if n.split(':')[1].split('#')[0] in PRE_FILTER_PORTS]
        after = len(nodes)
        ports_display = ', '.join(PRE_FILTER_PORTS)
        print(f"前置端口过滤（仅保留端口 {ports_display}）：{before} -> {after} 个节点")
        if not nodes:
            print("前置端口过滤后无任何节点，退出程序。")
            sys.exit(0)

    # 前置黑名单过滤
    if PRE_FILTER_BLOCKED_ENABLED and PRE_FILTER_BLOCKED_COUNTRIES:
        before = len(nodes)
        blocked_set = set(PRE_FILTER_BLOCKED_COUNTRIES)
        nodes = [n for n in nodes if n.split('#')[-1].upper() not in blocked_set]
        after = len(nodes)
        print(f"前置黑名单过滤：{before} -> {after} 个节点（已屏蔽：{', '.join(sorted(blocked_set))}）")
        if not nodes:
            print("前置黑名单过滤后无任何节点，退出程序。")
            sys.exit(0)

    if FILTER_COUNTRIES_ENABLED and ALLOWED_COUNTRIES:
        before = len(nodes)
        allowed_set = {c.upper() for c in ALLOWED_COUNTRIES}
        filtered_nodes = []
        for node in nodes:
            parts = node.split('#')
            if len(parts) == 2 and parts[1].upper() in allowed_set:
                filtered_nodes.append(node)
        nodes = filtered_nodes
        after = len(nodes)
        print(f"\n国家过滤（测试前）：{before} -> {after} 个节点（允许国家：{', '.join(allowed_set)}）")
        if not nodes:
            print("过滤后无任何节点，退出程序。")
            sys.exit(0)

    total = len(nodes)
    print(f"开始 TCP 连接测试（超时 {TIMEOUT}s，并发 {MAX_WORKERS}）...")

    results = []
    completed = 0
    last_print = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_node, node): node for node in nodes}
        for future in as_completed(futures):
            completed += 1
            res = future.result()
            if res:
                results.append(res)
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    print("\nTCP 测试完成！")
    if not results:
        print("没有通过成功率筛选的节点，请检查网络或降低 MIN_SUCCESS_RATE。")
        sys.exit(0)

    results.sort(key=lambda x: (-x[3], x[1]))
    latency_map = {node: lat for node, lat, _, _ in results}

    if USE_GLOBAL_MODE:
        candidates = [node for node, _, _, _ in results[:BANDWIDTH_CANDIDATES]]
        print(f"\nTCP 最优前 {len(candidates)} 个节点进入候选池。")
    else:
        country_nodes = defaultdict(list)
        for node_str, lat, country, succ in results:
            country_nodes[country].append((node_str, lat, succ))

        total_countries = len(country_nodes)
        base_limit = max(1, BANDWIDTH_CANDIDATES // total_countries)
        candidates = []
        for country, nodes_list in country_nodes.items():
            nodes_sorted = sorted(nodes_list, key=lambda x: (-x[2], x[1]))
            limit = min(len(nodes_sorted), base_limit)
            for node_str, lat, succ in nodes_sorted[:limit]:
                candidates.append(node_str)
        print(f"\n各国家候选池分配：共 {total_countries} 个国家，每国最多 {base_limit} 个候选，总计 {len(candidates)} 个节点进入候选池。")

    if not candidates:
        print("没有候选节点，退出。")
        sys.exit(0)

    candidates_after_availability, avail_ip_info, avail_exit_details = availability_filter_with_retry(candidates)
    candidates_after_http = http_server_filter(candidates_after_availability, cfg)

    bw_results = []
    for attempt in range(1, BANDWIDTH_RETRY_MAX + 1):
        print(f"\n[带宽测速] 第 {attempt} 轮测试...")
        bw_results = bandwidth_filter(candidates_after_http)
        if bw_results:
            break
        if attempt < BANDWIDTH_RETRY_MAX:
            print(f"本轮测速无有效结果，等待 {BANDWIDTH_RETRY_DELAY} 秒后重试...")
            time.sleep(BANDWIDTH_RETRY_DELAY)

    if not bw_results:
        print("\n带宽测速多次重试仍无有效结果，将使用 TCP 筛选结果作为最终节点。")
        send_wxpusher_notification(
            content=f"带宽测速经 {BANDWIDTH_RETRY_MAX} 轮尝试后仍无有效结果，已降级使用 TCP 排序节点。",
            summary="带宽测速全部失败"
        )
        if USE_GLOBAL_MODE:
            final_selected = [node for node, _, _, _ in results[:GLOBAL_TOP_N]]
        else:
            final_selected = []
            for country, nodes_list in country_nodes.items():
                nodes_sorted = sorted(nodes_list, key=lambda x: (-x[2], x[1]))
                for node_str, _, _ in nodes_sorted[:PER_COUNTRY_TOP_N]:
                    final_selected.append(node_str)
    else:
        if USE_GLOBAL_MODE:
            final_selected = [node for node, _ in bw_results[:GLOBAL_TOP_N]]
        else:
            country_speed_nodes = defaultdict(list)
            for node, speed in bw_results:
                country = node.split('#')[-1] if '#' in node else ''
                if country:
                    country_speed_nodes[country].append((node, speed))
            final_selected = []
            for country, nodes_list in country_speed_nodes.items():
                for node, speed in nodes_list[:PER_COUNTRY_TOP_N]:
                    final_selected.append(node)
            speed_map = {node: speed for node, speed in bw_results}
            final_selected.sort(key=lambda x: speed_map.get(x, 0), reverse=True)

        print("\n================ 最终优选节点 ================")
        speed_map = {node: speed for node, speed in bw_results}
        for i, node in enumerate(final_selected, 1):
            speed = speed_map.get(node, 0)
            lat_sec = latency_map.get(node, float('inf'))
            if lat_sec != float('inf'):
                print(f"{i}. {node} 速度 {speed:.2f} Mbps 延迟 {lat_sec*1000:.2f} ms")
            else:
                print(f"{i}. {node} 速度 {speed:.2f} Mbps")

    write_ip_txt(final_selected, OUTPUT_FILE,
                 AD_HEADER_ENABLED, AD_HEADER_LINES,
                 AD_FOOTER_ENABLED, AD_FOOTER_LINES,
                 AD_PERLINE_ENABLED, AD_PERLINE_TEXT,
                 speed_map=speed_map,
                 latency_map=latency_map)
    print(f"\n结果已保存到 {OUTPUT_FILE}（共 {len(final_selected)} 个节点）")

    ip_list = [node.split(':')[0] for node in final_selected]

    batch_update_cloudflare_dns(
        ip_list,
        ip_info=avail_ip_info,
        full_bw_results=bw_results,
        target_count=None,
        latency_map=latency_map
    )

    sync_to_github()

if __name__ == "__main__":
    import atexit

    enable_log = ENABLE_LOGGING
    log_filename = LOG_FILE

    if enable_log:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(script_dir, log_filename)
            log_f = open(log_path, "w", encoding="utf-8")
            print("日志已启用，输出将保存到 " + log_path)
        except Exception as e:
            print(f"无法打开日志文件 {log_path}: {e}")
            log_f = None
        else:
            class _Tee:
                def __init__(self, *files):
                    self.files = files
                def write(self, obj):
                    for f in self.files:
                        f.write(obj)
                        f.flush()
                def flush(self):
                    for f in self.files:
                        f.flush()
            sys.stdout = _Tee(sys.stdout, log_f)

            def _close_log():
                try:
                    sys.stdout = sys.__stdout__
                    log_f.close()
                except Exception:
                    pass
            atexit.register(_close_log)

    main()
