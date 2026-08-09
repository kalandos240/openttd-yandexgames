#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Could not patch {label}: {path}')
    path.write_text(text.replace(old, new, 1))


# The Yandex edition deliberately ships without downloadable AI modules and
# without Online Content. If an old save or an in-session setting still creates
# an AI company, use OpenTTD's dummy controller silently instead of displaying
# the stock "download it through Online Content" technical message.
ai_instance = Path('openttd/src/ai/ai_instance.cpp')
replace_once(
    ai_instance,
    'Script_CreateDummy(this->engine->GetVM(), STR_ERROR_AI_NO_AI_FOUND, "AI");',
    'Script_CreateDummy(this->engine->GetVM(), STR_NULL, "AI");',
    'AI dummy fallback message',
)

# STR_NULL is used only by our offline AI fallback above. Make the generic dummy
# script support a no-message mode: it still provides a valid no-op controller,
# but emits no AILog.Error line and therefore no red technical popup.
dummy = Path('openttd/src/script/script_info_dummy.cpp')
old = '''\tstd::string error_message = GetString(string);\n\tstd::vector<std::string> messages = EscapeQuotesAndSlashesAndSplitOnNewLines(error_message);'''
new = '''\tstd::string error_message;\n\tstd::vector<std::string> messages;\n\tif (string != STR_NULL) {\n\t\terror_message = GetString(string);\n\t\tmessages = EscapeQuotesAndSlashesAndSplitOnNewLines(error_message);\n\t}'''
replace_once(dummy, old, new, 'silent dummy script mode')

print('Offline AI fallback technical message disabled.')
