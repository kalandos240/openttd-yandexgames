#!/usr/bin/env python3
"""V8 native mobile touch semantics for OpenTTD placement tools.

The V7 bridge only knew whether a placement tool was active. That was not
sufficient: fixed-placement tools (depots, tunnels, large objects, docks, etc.)
were treated like drag tools, so crossing the finger movement threshold sent an
LMB-down at the original touch point and the object was built before the user
had finished choosing a position.

V8 adds a native per-window placement hint:
- drag placement: roads, rails, signals, terrain areas, canals, trees, etc.;
- release placement: fixed objects/structures and all unclassified tools.

The browser layer can therefore move the native hover preview under the finger
without pressing LMB, and commit fixed placement only on touch release.
"""
from pathlib import Path

ROOT = Path('openttd')


def replace_once(rel: str, old: str, new: str) -> None:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f'Missing OpenTTD source: {path}')
    text = path.read_text(encoding='utf-8')
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Anchor mismatch in {rel}: count={count}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


# ---------------------------------------------------------------------------
# 1. Give every Window a conservative touch-placement policy.
#    Default is release-only: this is the safe behaviour for fixed structures
#    and prevents accidental construction while the finger is still moving.
# ---------------------------------------------------------------------------
window_gui_old = """\tvirtual void OnPlaceObject([[maybe_unused]] Point pt, [[maybe_unused]] TileIndex tile) {}\n"""
window_gui_new = window_gui_old + r'''

	/**
	 * Whether a touch placement should start the original mouse drag sequence
	 * after the finger exceeds the movement threshold. Fixed placement tools
	 * intentionally keep the default false and are committed on touch release.
	 */
	virtual bool WantsTouchDragPlacement() const { return false; }
'''
replace_once('src/window_gui.h', window_gui_old, window_gui_new)


# ---------------------------------------------------------------------------
# 2. Road/tram toolbar. Everything except depot and tunnel placement is a
#    real sizing/drag operation in OpenTTD (including road stops/waypoints).
# ---------------------------------------------------------------------------
road_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n"""
road_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		switch (this->last_started_action) {
			case WID_ROT_ROAD_X:
			case WID_ROT_ROAD_Y:
			case WID_ROT_AUTOROAD:
			case WID_ROT_DEMOLISH:
			case WID_ROT_BUILD_WAYPOINT:
			case WID_ROT_BUS_STATION:
			case WID_ROT_TRUCK_STATION:
			case WID_ROT_BUILD_BRIDGE:
			case WID_ROT_CONVERT_ROAD:
				return true;

			case WID_ROT_DEPOT:
			case WID_ROT_BUILD_TUNNEL:
			default:
				return false;
		}
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
'''
replace_once('src/road_gui.cpp', road_anchor, road_insert)


# ---------------------------------------------------------------------------
# 3. Rail toolbar. Fixed station placement is release-only when station
#    drag/drop is disabled; station removal and drag/drop sizing remain drag.
# ---------------------------------------------------------------------------
rail_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n"""
rail_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		switch (this->last_user_action) {
			case WID_RAT_BUILD_NS:
			case WID_RAT_BUILD_X:
			case WID_RAT_BUILD_EW:
			case WID_RAT_BUILD_Y:
			case WID_RAT_AUTORAIL:
			case WID_RAT_DEMOLISH:
			case WID_RAT_BUILD_WAYPOINT:
			case WID_RAT_BUILD_SIGNALS:
			case WID_RAT_BUILD_BRIDGE:
			case WID_RAT_CONVERT_RAIL:
				return true;

			case WID_RAT_BUILD_STATION:
				return this->IsWidgetLowered(WID_RAT_REMOVE) || _settings_client.gui.station_dragdrop;

			case WID_RAT_BUILD_DEPOT:
			case WID_RAT_BUILD_TUNNEL:
			default:
				return false;
		}
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
'''
replace_once('src/rail_gui.cpp', rail_anchor, rail_insert)


# ---------------------------------------------------------------------------
# 4. Terraform toolbar. Area tools drag; sign placement is release-only.
# ---------------------------------------------------------------------------
terraform_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n"""
terraform_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		switch (this->last_user_action) {
			case WID_TT_LOWER_LAND:
			case WID_TT_RAISE_LAND:
			case WID_TT_LEVEL_LAND:
			case WID_TT_DEMOLISH:
			case WID_TT_BUY_LAND:
				return true;

			case WID_TT_PLACE_SIGN:
			default:
				return false;
		}
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
'''
replace_once('src/terraform_gui.cpp', terraform_anchor, terraform_insert)


# ---------------------------------------------------------------------------
# 5. Water toolbar. Canals/rivers/demolition select an area. Locks, depots,
#    docks, buoys and aqueducts are position-based and must wait for release.
# ---------------------------------------------------------------------------
dock_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n"""
dock_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		switch (this->last_clicked_widget) {
			case WID_DT_CANAL:
			case WID_DT_DEMOLISH:
			case WID_DT_RIVER:
				return true;

			case WID_DT_LOCK:
			case WID_DT_DEPOT:
			case WID_DT_STATION:
			case WID_DT_BUOY:
			case WID_DT_BUILD_AQUEDUCT:
			default:
				return false;
		}
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
'''
replace_once('src/dock_gui.cpp', dock_anchor, dock_insert)


# ---------------------------------------------------------------------------
# 6. Trees always use OpenTTD's sizing/drag path.
# ---------------------------------------------------------------------------
tree_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n"""
tree_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		return true;
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
'''
replace_once('src/tree_gui.cpp', tree_anchor, tree_insert)


# ---------------------------------------------------------------------------
# 7. Object picker: OpenTTD deliberately supports area-drag only for 1x1
#    objects. Larger objects are immediate placement on desktop, therefore on
#    touch they must remain preview-only until the finger is released.
# ---------------------------------------------------------------------------
object_anchor = """\tvoid OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override\n\t{\n\t\tconst ObjectSpec *spec = ObjectClass::Get(_object_gui.sel_class)->GetSpec(_object_gui.sel_type);\n"""
object_insert = r'''	bool WantsTouchDragPlacement() const override
	{
		const ObjectSpec *spec = ObjectClass::Get(_object_gui.sel_class)->GetSpec(_object_gui.sel_type);
		return spec != nullptr && spec->size == OBJECT_SIZE_1X1;
	}

	void OnPlaceObject([[maybe_unused]] Point pt, TileIndex tile) override
	{
		const ObjectSpec *spec = ObjectClass::Get(_object_gui.sel_class)->GetSpec(_object_gui.sel_type);
'''
replace_once('src/object_gui.cpp', object_anchor, object_insert)


# ---------------------------------------------------------------------------
# 8. Export richer native context from window.cpp. This runs after
#    patch-yandex-mobile-native.py, which already created the Emscripten block
#    containing em_openttd_touch_pan().
#
#    0 = GUI / no viewport
#    1 = map viewport, no placement tool -> one-finger pan
#    2 = active placement tool that wants original LMB drag
#    3 = active fixed-placement tool -> hover while held, click on release
# ---------------------------------------------------------------------------
window = ROOT / 'src/window.cpp'
text = window.read_text(encoding='utf-8')
context_marker = 'Yandex mobile touch context V8: drag tools versus release placement.'
if context_marker not in text:
    pan_marker = '/* Yandex mobile direct touch pan: bypass desktop mouse-scroll state. */'
    start = text.find(pan_marker)
    if start < 0:
        raise SystemExit('Could not locate direct-pan marker in window.cpp')
    end = text.find('\n#endif', start)
    if end < 0:
        raise SystemExit('Could not locate Emscripten #endif after direct-pan marker')

    addition = r'''

/* Yandex mobile touch context V8: drag tools versus release placement.
 * Return values:
 *   0 = regular OpenTTD UI / no usable viewport
 *   1 = viewport with no active placement tool (one-finger pan)
 *   2 = viewport with a drag-placement tool (original LMB drag)
 *   3 = viewport with a fixed-placement tool (hover, commit on release)
 */
extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_touch_context(int x, int y)
{
	Window *w = FindWindowFromPt(x, y);
	if (w == nullptr) return 0;

	Viewport *vp = IsPtInWindowViewport(w, x, y);
	if (vp == nullptr || _game_mode == GM_MENU || HasModalProgress()) return 0;
	if (_thd.place_mode == HT_NONE) return 1;

	Window *owner = _thd.GetCallbackWnd();
	return owner != nullptr && owner->WantsTouchDragPlacement() ? 2 : 3;
}
'''
    text = text[:end] + addition + text[end:]
    window.write_text(text, encoding='utf-8')

print('Yandex mobile V8 native drag-vs-release placement semantics applied')
