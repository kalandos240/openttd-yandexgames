#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Could not patch {label}: {path}')
    path.write_text(text.replace(old, new, 1))


# This Yandex edition does not ship the Online Content service, so it must not
# create new AI competitors that would require downloadable AI packages.
ai_core = Path('openttd/src/ai/ai_core.cpp')
replace_once(
    ai_core,
    '''/* static */ bool AI::CanStartNew()\n{\n\t/* Only allow new AIs on the server and only when that is allowed in multiplayer */\n\treturn !_networking || (_network_server && _settings_game.ai.ai_in_multiplayer);\n}''',
    '''/* static */ bool AI::CanStartNew()\n{\n\t/* Yandex edition: downloadable AI modules / Online Content are intentionally disabled. */\n\treturn false;\n}''',
    'AI::CanStartNew hard-disable',
)

# A loaded save can still contain an AI company. In that case OpenTTD falls
# back to its built-in dummy controller. Pass a private no-message sentinel so
# it never emits the stock "AI modules are missing / download Online Content"
# error popup.
ai_instance = Path('openttd/src/ai/ai_instance.cpp')
replace_once(
    ai_instance,
    'Script_CreateDummy(this->engine->GetVM(), STR_ERROR_AI_NO_AI_FOUND, "AI");',
    'Script_CreateDummy(this->engine->GetVM(), INVALID_STRING_ID, "AI");',
    'AI dummy fallback message',
)

# Teach the generic dummy script about the sentinel. For the no-message Yandex
# fallback it becomes a harmless sleeping controller instead of logging an
# error and immediately dying. This also handles old savegames containing AI
# companies without showing any red script/debug window.
dummy = Path('openttd/src/script/script_info_dummy.cpp')
old_message = '''\tstd::string error_message = GetString(string);\n\tstd::vector<std::string> messages = EscapeQuotesAndSlashesAndSplitOnNewLines(error_message);'''
new_message = '''\tstd::string error_message;\n\tstd::vector<std::string> messages;\n\tif (string != INVALID_STRING_ID) {\n\t\terror_message = GetString(string);\n\t\tmessages = EscapeQuotesAndSlashesAndSplitOnNewLines(error_message);\n\t}'''
replace_once(dummy, old_message, new_message, 'silent dummy script mode')

old_body = '''\tformat_append(dummy_script, "class Dummy{0} extends {0}Controller {{\\n  function Start()\\n  {{\\n", type);\n\tfor (std::string &message : messages) {\n\t\tformat_append(dummy_script, "    {}Log.Error(\\\"{}\\\");\\n", type, message);\n\t}\n\tdummy_script += "  }\\n}\\n";'''
new_body = '''\tformat_append(dummy_script, "class Dummy{0} extends {0}Controller {{\\n  function Start()\\n  {{\\n", type);\n\tif (messages.empty()) {\n\t\t/* Offline/Yandex fallback: stay alive silently so ScriptInstance does not report a dead AI. */\n\t\tdummy_script += "    while (true) { this.Sleep(365); }\\n";\n\t} else {\n\t\tfor (std::string &message : messages) {\n\t\t\tformat_append(dummy_script, "    {}Log.Error(\\\"{}\\\");\\n", type, message);\n\t\t}\n\t}\n\tdummy_script += "  }\\n}\\n";'''
replace_once(dummy, old_body, new_body, 'persistent silent dummy controller')

print('AI competitors hard-disabled; missing-AI fallback is silent and persistent.')
