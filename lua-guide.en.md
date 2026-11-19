# Lua: quick start

**Русская версия:** [lua-guide.md](lua-guide.md)

This is a guide for HvH script authors. The full list of functions, events and limits: [lua-api.en.md](lua-api.en.md).

## Loading

1. Open the menu → **Config**. Lua is to the right of the configs.
2. Paste the contents of the `.lua` file into the editor, give it a name and press **Load / reload**.
3. The script's own controls appear below the Lua buttons — scroll the right column.
4. **Save source** stores the source in your private profile. After joining, the script has to be loaded by hand.
5. **Unload** removes the script's drawings, 3D effects, callbacks and overrides.

Values of the Lua controls are not saved to the profile automatically. `storage` keeps data between reloads in the current game session, but not between joins.

## Two ready examples

| File | What it does | On right away |
| --- | --- | --- |
| [starter-hud.lua](lua-examples/starter-hud.lua) | A separate FPS counter, frame time graph or shapes; pick the **Element**, set the color | FPS counter |
| [starter-hitlog.lua](lua-examples/starter-hitlog.lua) | Your confirmed hits / misses, hitgroup, damage, remaining HP, kill; optional real 3D tracers | Hitlog and tracers of your shots |

The hitlog appears after a shot, not right after loading. It does not turn rage on and does not change any shooting settings. A miss message is only possible for a shot with a rage target and an available server result; no reason is made up for a plain bullet that missed.

Other examples:

- [aa-builder-extended.lua](lua-examples/aa-builder-extended.lua): five conditions, packet jitter, pitch, body amount and side. After loading, turn on **Extended AA builder**.
- [custom-camera.lua](lua-examples/custom-camera.lua): thirdperson, shoulder, distance, FOV and roll. Turned on with the **Lua camera** checkbox.
- [rage-hooks.lua](lua-examples/rage-hooks.lua): damage / HC, target filter, point score and shot veto. **Lua rage rules** is off at first.
- [resolver.lua](lua-examples/resolver.lua): an example of your own body hypothesis; off by default. It demonstrates the API, it does not promise better accuracy.
- [impact-effects.lua](lua-examples/impact-effects.lua): spheres, rings, particles and 3D text from real shots.
- [grenade-warning.lua](lua-examples/grenade-warning.lua): the path of grenades in flight, a landing marker through walls, a timer and a warning when an enemy one lands near you (`entity.get_grenades`, `through_walls`).
- [bomb-legit-aa.lua](lua-examples/bomb-legit-aa.lua): your own AA during a plant / defuse (`bomb_action`, needs AA > Other "Anti-aim on bomb actions") and your own body side while Legit anti-aim is held (`legit_aa`).
- [hysteria-image-test.lua](lua-examples/hysteria-image-test.lua): an original PNG caption embedded in the source, nothing uploaded to Roblox.
- [extended-visuals.lua](lua-examples/extended-visuals.lua): draggable panel, clipping, a timer, a hotkey and session storage.
- [gui-showcase.lua](lua-examples/gui-showcase.lua): your own menu on `gui.*` — every widget, themes, own binds, links to game settings, notifications (RightShift).

## Script structure

```lua
local enabled = ui.new_checkbox('My script')
ui.set(enabled, true)

client.set_event_callback('paint', function()
    if not ui.get(enabled) then return end
    renderer.text(30, 100, 255, 255, 255, 255, 'hello', 18)
end)
```

Create controls, PNG textures and callbacks once, while loading. In `paint` draw the whole frame again: an element not drawn in the new frame is hidden. Do not create checkboxes or decode PNGs in `paint`.

By default controls appear in Config > Lua. An AA builder (or any other script) can take a tab over: `ui.override_tab('AA')` — the built-in groups are hidden and the script's controls take their place, split into groups with `ui.set_group(id, 'Builder')`. The built-in settings keep working meanwhile, and after Unload the tab comes back as it was. Example: `lua-examples/aa-builder-extended.lua`.

## Which event to use

| Task | Callback |
| --- | --- |
| Panel, indicator, ESP, animation | `paint` |
| Drawing after the normal paint, including in the menu | `paint_ui` |
| A real shot and its result | `shot` |
| A confirmed hit with a known source | `player_hurt` |
| Your rage hit / missed | `aim_hit` / `aim_miss` |
| New public state of the players | `net_update_end` |
| Round change / bomb state | `round_start`, `round_end`, `bomb_*` |
| Your own angles and desync | `anti_aim` |
| Rage settings for the current call | `rage_config` |
| Filter / prioritize a target, record or point | `rage_target`, `rage_record`, `rage_point` |
| Final veto of a prepared shot | `rage_fire` |
| Your own hypothesis of the target's body | `resolve` |
| Visual camera | `override_view` |

`aim_fire` is a predicted intention to shoot; it does not prove a hit. For a hitlog use the server's `shot` or `player_hurt`. Snapshot events have `observed=true`: an intermediate state may have been missed by the received packet. Fall / bomb damage shows up through `player_health`, without a made-up attacker.

Game data tables are copies. Changing them does not change the game. Writable callbacks work only through the fields listed in the API: for example `c.yaw` in `anti_aim` or `v.fov` in `override_view`. To pick your own hypothesis, `resolve` returns an angle.

## Coordinates, colors and time

- Screen coordinates and 2D line thickness are pixels.
- World coordinates, 3D effect sizes and tracer widths are **hu**, 12 hu = 1 Roblox stud.
- `vector.new(x,y,z)` creates a Vector3; the vertical axis is Y.
- Colors are RGBA 0…255, alpha 255 is fully opaque.
- Angles are degrees, the camera FOV is horizontal.
- `globals.realtime()` suits local animations / fades; `globals.curtime()` is server time.
- `globals.frametime()` is in seconds: multiply by 1000 for milliseconds.

## Real 3D tracers

```lua
client.set_event_callback('bullet_impact', function(e)
    if e.shooter ~= entity.get_local_player() then return end
    if (e.impact - e.start).Magnitude <= .001 then return end
    renderer.tracer(e.start, e.impact, {
        color={125,209,255,255}, width=2,
        end_width=.5, life=1, fade=.3, glow=1,
    })
end)
```

This is an engine Beam in the world, hidden by geometry as usual. Create it once per event, not every `paint`. Lifetime and cleanup are handled automatically. A colored glow does not mean Bloom gets turned on. An embedded PNG handle cannot be passed as a Beam `texture`: Beam textures use an `rbxassetid://` available to the game.

## Images

```lua
local logo = renderer.load_png_base64('...your Base64 PNG...')
client.set_event_callback('paint', function()
    renderer.texture(logo, 30, 100, 128, 64, 255,255,255,255)
end)
```

The string above is a placeholder, not a valid PNG. A working example is in `hysteria-image-test.lua`. A white tint keeps the original colors. PNG / RGBA are supported; JPEG / SVG and interlaced / 16-bit PNGs are not. Load an image once; later frames use the handle. On unload the engine frees the memory.

## Performance

Draw only what you need, keep log / point lists bounded, remove expired entries. For a graph, create a fixed-length buffer up front. Run heavy calculations on a snapshot / timer, not again for every line. `rage_point` may be called many times — keep the callback short.

| Limit | Per script |
| --- | --- |
| Source | run up to 400 KiB, save up to 192 KiB |
| 2D primitives | 384 per frame |
| Controls | 48 |
| PNG / RGBA | up to 256×256, 32 textures / 1 MiB of pixels |
| Active 3D tracers | 64; up to 16 new per frame |
| Active 3D effects | 32; up to 16 new per frame; up to 4 lights |
| Timers | 32; repeating with an interval from .05 s |
| world / bullet traces | 128 per frame |
| Public poses | 64 builds per frame |

A script gets 10 ms of VM work per frame; loading (code outside callbacks) gets 2 s. An error or a budget overrun inside a callback aborts only that call: the script stays loaded, the next frame calls the callback again, and the message is shown in the Lua output (repeats are counted as `+N more`). A script is turned off only by an error while loading. Command changes and rage hook answers from an aborted call are not applied. This does not guarantee full isolation of every native operation.

In the `execution budget exceeded` error, `frame time` means the frame's 10 ms ran out, `load time` — the 2 s of loading. `event` shows the event, `instructions` the instruction count of the current call, `frame` the accumulated time. The time is shared by all of the script's callbacks, including repeated `resolve` and rage hook calls in a frame; once it runs out, the script's remaining callbacks in that frame are skipped.

A source larger than ~195 KiB does not fit into one Roblox text field: paste the first part, press **Add as part**, paste the next one and so on, then **Load / reload** (the parts are joined in order, **Clear parts** resets them). A script up to 400 KiB runs (more does not fit into the compiler's memory; compiling 400 KiB takes a few seconds), but **Save source** saves only up to 192 KiB: a larger script works until you leave the game, then it has to be pasted again.

Errors look like `line 12 (draw): attempt to index nil with 'x' [from line 30 (paint_esp) <- line 41]`: first the line and function where it failed, then the call chain. Syntax errors look like `line N: ...`.

## Compatibility and common mistakes

- Partly compatible with gamesense: `ui.new_*("TAB", "Group", "Name", ...)` (combo boxes / multiselects of this form are read and written by option names, `ui.contains` exists), `renderer.text(x, y, r, g, b, a, flags, max_width, ...)` with the flags `c r b - +`, `renderer.measure_text(flags, ...)`, `renderer.circle(..., radius, start, percentage)`, `circle_outline`, `indicator`, `client.key_state(0x41)` (virtual key codes), `client.color_log/random_int/random_float/unix_time/system_time`, `globals.absoluteframetime/mapname/maxplayers`, `entity.get_prop` with `m_iHealth/m_ArmorValue/m_fFlags/m_vecOrigin`, `require "vector"` (the gamesense vector) and `require "bit"`. Unknown events (`run_command` etc.) are ignored; their list is shown after loading. FFI, `require "gamesense/..."` and `ui.reference` by gamesense menu names are not available — for settings use the keys from `ui.list_settings()`. No real `game` / `workspace`, remotes or arbitrary Instances; HTTP (`game:HttpGet`, `request`, `http.*`), files (`readfile` / `writefile`...), `task.*` and `loadstring` exist, see lua-api.en.md.
- Combo boxes are **1-based**. `ui.get(color)` returns four numbers, not a Color3.
- An error in a callback does not turn the script off, but that call is aborted; check the output line under Lua. An error while loading turns the script off.
- The usual standard library is there: `string.gsub/gmatch/find/match/format`, string methods (`s:sub()`, `s:gsub()`), `os.clock/time/date`, `setmetatable/getmetatable` (classes through `__index`), `rawget/rawset`, `_G`, `coroutine`, `utf8`, `table.move`, `bit.tobit/tohex/arshift/rol/ror`, `math.modf/log10/noise`, `collectgarbage("count")`. Tables passed by the game (event arguments, `entity.get` etc.) cannot get a metatable — copy the fields into your own table.
- `world_to_screen` can return nil — check it before drawing.
- No logs without shots is normal. Events are not replayed after Load.
- The opponent's real hidden angles are not available. `resolve` is an assumption; `trace_bullet` is an ideal estimate, not a guaranteed real hit.
- The camera changes the picture, not the direction of server shots.
- Unload the previous version before testing a new script. Overrides of several Lua scripts stack; the last valid write wins, unload restores the previous value.

## Protecting your code

Nobody is protected from source theft: an executor can dump any code that runs on the client. But it can be made much harder. Run your script through an obfuscator (Prometheus, luaobfuscator, MoonSec, Luraph...) and publish the result with **Publish sealed**: the source stays with you, everyone else gets only bytecode by code, without variable names or line numbers. Details in lua-api.en.md, "Sealed scripts" and "Protecting your code from copying".
