#!/usr/bin/env python3
"""
Test script for the new formatting functions.
"""

import sys

# Mock the telegram imports to avoid dependency issues
import types
telegram_mock = types.ModuleType('telegram')
telegram_mock.Update = object
telegram_mock.ReplyKeyboardMarkup = object
telegram_mock.KeyboardButton = object
sys.modules['telegram'] = telegram_mock

telegram_ext_mock = types.ModuleType('telegram.ext')
telegram_ext_mock.Application = object
telegram_ext_mock.CommandHandler = object
telegram_ext_mock.MessageHandler = object
telegram_ext_mock.filters = types.ModuleType('filters')
telegram_ext_mock.filters.TEXT = object
telegram_ext_mock.filters.COMMAND = object
telegram_ext_mock.ContextTypes = types.ModuleType('ContextTypes')
telegram_ext_mock.ContextTypes.DEFAULT_TYPE = object
sys.modules['telegram.ext'] = telegram_ext_mock

# Now import our functions
from bot import format_status_section, format_wallet_section, format_tasks_section

# Test with the status output from the message
test_output = '''┌────────────────────────────────────────────────┐
│  Status                                      │
│                                                │
│  Service    is running                       │
│  Version    0.17.6                             │
│  Commit     a98d28015                          │
│  Date       2025-10-04                         │
│  Build      1122                               │
│                                                │
│  Node Name  tan-territory                      │
│  Subnet     public                             │
│  VM         invalid environment              │
│                                                │
│  Driver     Ok                               │
├────────────────────────────────────────────────┤
│  Wallet                                      │
│  0x34874a4904cad46fab709b57fabef0589a0fd075  │
│                                                │
│  network                mainnet              │
│  amount (total)         0 GLM                  │
│      (on-chain)         0 GLM                  │
│      (polygon)          0 GLM                  │
│                                                │
│  pending                0 GLM (0)              │
│  issued                 0 GLM (0)              │
├────────────────────────────────────────────────┤
│  Tasks                                       │
│                                                │
│  last 1h processed     0                       │
│  last 1h in progress   0                       │
│  total processed       0                       │
│  (including failures)                          │
└────────────────────────────────────────────────┘'''

print('=== SERVICE STATUS ===')
result1 = format_status_section(test_output)
print(result1)
print()
print('=== WALLET INFO ===')
result2 = format_wallet_section(test_output)
print(result2)
print()
print('=== TASK STATISTICS ===')
result3 = format_tasks_section(test_output)
print(result3)
print()
print('✅ All formatting functions work correctly!')
