# Contributing

Thanks for helping improve the OpenTTD Yandex Games port.

## Before opening an issue

Please check whether the problem is specific to this browser/Yandex Games port.

- If the same bug happens in the official OpenTTD 15.3 desktop release, report it to the upstream OpenTTD project.
- If the problem concerns startup, WebAssembly, browser storage, Yandex Games SDK integration, localization packaging or the generated ZIP, it belongs here.

## Pull requests

Keep changes focused on the porting and packaging layer whenever possible. Avoid vendoring the full OpenTTD source tree into this repository.

For build-related changes, describe:

- what part of the pipeline changes;
- why the change is needed;
- whether it affects the generated package;
- how the change was tested.

The reference build path is the **Final OpenTTD Package** GitHub Actions workflow.

## Licensing

Do not add third-party code, graphics, sound, music or other assets unless their redistribution terms are understood and their required notices can be preserved. See `THIRD_PARTY_NOTICES.md` for the components currently used by the build.
