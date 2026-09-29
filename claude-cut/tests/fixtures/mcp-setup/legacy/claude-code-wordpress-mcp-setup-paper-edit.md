# Paper Edit: Connect Claude Code to WordPress with MCP (Then Lock It Down)

**Script:** `claude-code-wordpress-mcp-setup-script-v2.md`
**Built:** 23 September 2026
**Estimated runtime:** about 18:10 (roughly 2,490 spoken words at 150 words a minute, plus about 90 seconds of screen-recording dwell for typing, loading and holds)
**Aspect:** 16:9, 4K timeline if the screen recordings were captured at Retina resolution (so zooms stay sharp)

Timecodes are estimates from word count. Once the A-roll is cut, slide everything to match real delivery and update the chapter list at the bottom.

---

## Before anyone opens the timeline

The two problems flagged in the first pass have been fixed in the plugin code and the script now matches it:

1. **Resolved: `show_in_rest` has been removed.** The meta now has `'mcp' => array( 'public' => true )` and the 17:20 line says so. `show_in_rest` only controls the Abilities REST API, which is a separate thing from MCP. The adapter exposes abilities through `meta.mcp.public`, and they're private by default. Source: `docs/guides/creating-abilities.md` in WordPress/mcp-adapter.

2. **Resolved: the permission callback now checks `manage_casagees_slots`** instead of `read`, and only the claude-ai user has that capability. The 13:02 and 14:25 lines now agree with each other, and the padlock MG at 14:52 is earned.

The capability was granted per user with `wp user add-cap claude-ai manage_casagees_slots`, and the 14:35 beat now says so on camera. The docblock above `casagees_abilities_can_manage` has been updated to match.

Smaller pre-edit checks, carried over from the script's fact-check list:

- Grab the real SSH terminal transcript (about 10:52). The cold open promises it, so it has to be there.
- In the Shop Manager demo (about 9:35), keep Claude Code's tool-call lines visible so viewers can see the orders came through `mcp-adapter/execute-ability` and not through a side route.
- Blur list: application password (about 2:45), any real env values, SSH host, username, IP and key paths (about 10:52), and customer names or addresses in the order output (about 9:35).

---

## Tone and style for the whole piece

- **Overall feel:** someone who's been burnt showing you how not to get burnt. Warm, plain and a bit wry. The pace is steady, not frantic, because people will follow along step by step and pause.
- **Two gears.** Tutorial sections (steps 1 to 5) are calm and methodical, with generous holds on anything people need to copy. The story sections (cold open, guard rails) get tighter cuts and a bit more tension, with no music under the key admission lines.
- **Chapter cards** are the same template every time: number, title, a short wipe in and out, under a second each way. Consistency matters more than flair because this is a reference video people will scrub through.
- **The kitchen illustration** is the visual spine. It appears four times (sections 5, 8, 9 and optionally 11). Build it once as a layered file so each return reuses the same art with one thing changed. Keep it simple and flat, with padlocks on the jars that can animate on and off.
- **Code on screen:** use your editor theme at 150% zoom or larger, and highlight the line being spoken with a soft box rather than a flashing arrow. Don't show code that isn't being talked about.
- **Music:** a low, light bed under the tutorial sections. Drop it out completely for the SSH admission (0:02 and 10:20 to 11:05) and bring it back on the fix (11:12).
- **Captions:** burn in only the key terms (MCP, `.mcp.json`, Subscriber, `permission_callback`, `manage_casagees_slots`). Everything else goes in YouTube's closed captions.
- **Voice guide check:** no em-dashes in any on-screen text, and British spelling in every graphic ("organised", "colour", "licence").

---

## Beat-by-beat

Key: **A** = A-roll (talking head), **SR** = screen recording, **MG** = motion graphic, **LT** = lower third, **BR** = b-roll.

### 1. Cold open (0:00 to 1:30)

Purpose: hook with the SSH incident, then set up why this video exists. The first ten seconds decide retention, so the SSH line has to land before anything else.

| TC   | Spoken                                                                                                                           | On screen                                                                             | Transition                 | Notes                                                                                       |
| ---- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------- |
| 0:00 | *(no speech, 2s)*                                                                                                                | MG: the SSH terminal frame, heavily blurred, red "ACCESS" stamp slams in              | Hard cut from black        | Small sting or single low hit. No logo, no intro.                                           |
| 0:02 | "While I was testing this, Claude Code got into my live WordPress site over SSH..."                                              | A, medium close-up                                                                    | Hard cut                   | Deliver it flat and a bit rueful, not dramatic. Leave a half-beat pause after "over SSH".   |
| 0:10 | "...I'll show you exactly how that happened later, and how to stop it happening to you."                                         | A, punch in 10%                                                                       | Hard cut on "later"        | The punch-in marks the promise. Small "Later in the video" text top right, fading after 2s. |
| 0:16 | "Okay, so some of you are going to hate this. AI is everywhere..."                                                               | A, back to medium                                                                     | Hard cut                   | Music bed fades in quietly here.                                                            |
| 0:24 | "...spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI."                                     | BR: 3 to 4s of the Studio app with its AI chat panel open                             | L-cut (audio carries over) | Keep it honest: real Studio footage, not stock.                                             |
| 0:32 | "But I wanted to set up my own configuration, using Claude Code, talking to a real site."                                        | A                                                                                     | J-cut back                 |                                                                                             |
| 0:38 | "Now, there is official documentation for this... under the MCP Adapter repository..."                                           | SR: github.com/WordPress/mcp-adapter README, slow scroll                              | L-cut                      | Highlight "WordPress" in the org name so it reads as official.                              |
| 0:50 | "What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file." | SR continues, scroll lands on the sparse config example in the CLI guide              |                            | Soft box around the example to show how little is there.                                    |
| 1:00 | "So that's what this video is."                                                                                                  | A                                                                                     | Hard cut                   | Straight to camera, a small nod.                                                            |
| 1:04 | "For those of you who don't know, MCP stands for Model Context Protocol..."                                                      | A with LT: "MCP = Model Context Protocol. A standard way for AI to talk to software." | LT slides in               | Hold the LT for at least 4s.                                                                |
| 1:20 | "Keep that in your back pocket, because I'll give you a better analogy in a minute."                                             | A                                                                                     |                            | Tiny knowing smile. That sets up beat 5.                                                    |

### 2. Step one: the user (1:30 to 2:25)

Purpose: first practical step, with the lowest role as the message.

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 1:30 | *(chapter card)* | MG: "1. The user" | Graphic wipe | Same template for all five steps. |
| 1:32 | "The first thing to do happens on your live production site, not your local one..." | SR: production wp-admin, Users > Add New | Wipe out to SR | Blur the production URL in the address bar if you'd rather not show it. |
| 1:45 | "...I've called mine claude-ai, and I've given it a password I'm probably never going to log in with..." | SR: typing "claude-ai" into username | | Speed-ramp the form fill (2x) but keep the typing of "claude-ai" at real speed. |
| 1:58 | "The important bit is the role. Set it to the lowest possible, which is Subscriber." | SR: zoom to the role dropdown, select Subscriber | Punch-in zoom (ease, 0.4s) | **Key point.** Text callout "Lowest role that does the job", held 3s. |
| 2:08 | "A lot of the tutorials out there just generate the password on the admin account they're already logged in as..." | A | Hard cut to A | Direct to camera. Don't show or name any competitor's footage. |
| 2:20 | "...let it go wild on your site doing things you didn't expect." | A | | Wry delivery. |

### 3. Step two: the application password (2:25 to 3:10)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 2:25 | *(chapter card)* | MG: "2. The application password" | Graphic wipe | |
| 2:27 | "Next, on that same user, scroll down to Application Passwords and generate one." | SR: claude-ai profile, scroll to Application Passwords | Wipe to SR | Make sure the username "claude-ai" is visible at the top of the profile before scrolling. |
| 2:35 | "...an application password is a separate credential that lets a piece of software talk to your site..." | SR: hold on the section, soft box around it | | LT: "Application password: a login for software, not people." |
| 2:45 | "Give it a name, hit the button, and WordPress generates it for you and shows it once..." | SR: type a name, click, password appears | | **Blur the password** with a heavy blur, not a light mosaic. Add a small "copy it now" callout pointing at the copy action. |
| 2:57 | "So now we've got a username and an application password... They just sit there." | A | Hard cut | Sets up the "it does nothing on its own" running gag. |

### 4. Step three: install the MCP Adapter (3:10 to 4:15)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 3:10 | *(chapter card)* | MG: "3. The MCP Adapter" | Graphic wipe | |
| 3:12 | "Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory..." | SR: WordPress/mcp-adapter repo home | Wipe to SR | Keep "as far as I know" in. Don't put any "coming to the directory" text on screen, because it's unconfirmed. |
| 3:25 | "...the link is in the description." | SR, with a small "Link in description" tag | | |
| 3:30 | "The easiest way in is the Releases page on that repo, where there's a ready-made mcp-adapter.zip..." | SR: Releases page, zoom to the latest tag and the `mcp-adapter.zip` asset | Punch-in zoom | Record on filming day so the version number is current (v0.6.1 on 23 September 2026). |
| 3:42 | "Upload that through Plugins, Add New, on your live site, and activate it." | SR: Plugins > Add New > Upload > Install > Activate | | Speed-ramp the upload (3x), then real speed on the "Plugin activated" notice. |
| 3:52 | "(If you'd rather build it yourself, you can clone the repo...)" | SR: brief flash of a terminal `git clone` | Quick cut | 2s max. It's an aside, so keep it visually small. |
| 3:58 | "Again, on its own, it just sits there..." | MG: three icons (user, key, plugin) appear one at a time, each greyed out | Cut to MG over A (A in a corner bubble or full MG) | Sync each icon to its noun in the line. |
| 4:08 | "The magic is in how you put them together, and that's where the analogy comes in." | A | Hard cut | Lean in slightly. It's a turn in the video. |

### 5. The hatch and the cupboard (4:15 to 5:40)

Purpose: the mental model. It's the slowest section, so let it breathe. The illustration does the heavy lifting.

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 4:15 | "Imagine you're a chef (bear with me, I was one once)..." | A, then MG: kitchen illustration builds (wall, hatch) | Cross-dissolve into MG (the only dissolve in the video, which marks the shift into metaphor) | Let "I was one once" play on A before the MG takes over. |
| 4:25 | "The MCP server is the doorway into that cupboard. The hatch, if you like." | MG: hatch highlights, label "MCP server" | | |
| 4:32 | "Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API." | MG: cupboard opens, jars appear, label "Abilities" | | |
| 4:40 | "An ability is a single thing your site can do... creating a post, looking up an order or regenerating delivery slots." | MG: three jars get labels as each example is said | | Sync each label to its words. |
| 4:52 | "Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check..." | MG: an empty shelf gap, then padlocks appear on some jars | | **Key point.** Callout: "No registration, no jar." |
| 5:05 | "So some jars have a padlock on them and some are open, depending on who's asking..." | MG: a small figure labelled "Subscriber" at the hatch can reach only the unlocked jars | | |
| 5:15 | "What you really need to understand is that the key to the hatch is not the adapter plugin..." | A | Hard cut to A | Slow down. It's the key insight of the video. |
| 5:25 | "The key is the MCP configuration on your local machine." | MG: key appears on the chef's side, labelled ".mcp.json" | Cut to MG | Hold for 3s after the line. |
| 5:32 | "...and the abilities are what's on the shelves once you're in." | MG: key turns, hatch opens | | Clean end on the open hatch, then wipe to chapter 4. |

### 6. Step four: the config file (5:40 to 7:55)

Purpose: the most rewatched part of the video, because people will pause here. Prioritise legibility over pace.

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 5:40 | *(chapter card)* | MG: "4. The config file" | Graphic wipe | |
| 5:42 | "The official docs give you a basic config, but they don't tell you where it lives or how to build it..." | SR: editor, file tree of the project root | Wipe to SR | |
| 5:50 | "In your local project folder, create a file called .mcp.json..." | SR: new file created, name typed | | Zoom so the file tree and filename are readable. Callout: "Project root". |
| 5:58 | "From the MCP adapter GitHub docs, you can just copy this object..." | SR: split screen, GitHub CLI guide on the left and editor on the right | Split-screen wipe | 3s, then back to the editor full screen. |
| 6:06 | "At the top level we need an mcpServers object... I've called mine claude-ai to match the user." | SR: type `mcpServers`, then `claude-ai` | | Highlight each key as it's said. |
| 6:20 | "Now the guts of it. command is npx, and args is an array with -y and then @automattic/mcp-wordpress-remote@latest." | SR: type `command` and `args` | | Keep the typing real speed or 1.5x at most, and let every key get its highlight. |
| 6:32 | "That's the little bridge that runs on your machine and talks to the adapter on your site." | MG: flow of laptop > "mcp-wordpress-remote" > internet > site with adapter | Cut to MG, 4s | Match the jar and hatch art style. |
| 6:40 | "Then the environment variables. WP_API_URL is your site, followed by the route to the hatch..." | SR: type `WP_API_URL` | Cut back | Callout pinned under the line: `/wp-json/mcp/mcp-adapter-default-server`. |
| 6:55 | "I'm using the CasaGees site, which is the pizza delivery service we run from home..." | BR: 2 to 3s of the CasaGees homepage or a real pizza shot | L-cut | Human moment, so keep it light. Pizza footage beats a screenshot if you've got it. |
| 7:05 | "WP_API_USERNAME is the user you created, and WP_API_PASSWORD is the application password..." | SR: type both keys | | |
| 7:12 | "Now, for security reasons, I haven't pasted the real values in here..." | SR: zoom on `${WP_API_USERNAME}` and `${WP_API_PASSWORD}` | Punch-in | **Key point.** Callout: "Set these in the shell that launches Claude Code" (this covers the fact-check note on `${VAR}` expansion). |
| 7:25 | "Please don't be the numpty who pushes an application password to GitHub." | A | Hard cut | Comedy beat, so hold 1s after the line before cutting. |
| 7:30 | *(on the numpty line)* | MG: red warning strip, "Never commit real passwords. Add .mcp.json to .gitignore if in doubt." | Strip slides over A | Hold 4s. |
| 7:35 | "Finally, and just for sanity, there's LOG_FILE..." | SR: type `LOG_FILE` | | |
| 7:45 | "...when something goes wrong (and it will), that's where you look." | SR: the finished file, full view | | **Hold the full file for 5s minimum** with no overlays. Add "Config in description" text in the corner after 2s. |

### 7. Step five: connect (7:55 to 9:20)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 7:55 | *(chapter card)* | MG: "5. Connect" | Graphic wipe | |
| 7:57 | "With that in place, start a Claude Code session in the project..." | SR: terminal, `claude` launched in the project folder | Wipe to SR | Terminal font at 18pt or larger. |
| 8:05 | "The first thing it'll do is ask whether you want to use this MCP server, so say yes." | SR: zoom on the approval prompt | Punch-in | Callout on the "yes" choice. |
| 8:12 | "You could add this to your global Claude configuration... but I don't want that." | A | Hard cut | |
| 8:22 | "I want the control to sit inside the project... When I close the session, the connection closes with it..." | MG: simple toggle graphic, session open means connection on, session closed means connection off | Cut to MG | 4s. It's an optional MG, so drop it if the A-roll is strong. |
| 8:35 | "Now let's try it. I'm just going to ask the agent, 'can you see my site over MCP?'" | SR: typing the prompt | Hard cut | Real-speed typing. |
| 8:42 | *(waiting on the response)* | SR: response streaming in | Speed-ramp the wait | Ramp any dead air to 4x, and keep the tool-call line visible. |
| 8:50 | "And there you go. It comes back with information about the site... Sweet huh!" | SR: zoom on the site name in the response | Punch-in | Small payoff moment. Lift the music a touch. |
| 9:00 | "So, to recap what you actually need..." | MG: checklist builds (live site, minimum-role user, application password, MCP Adapter, `.mcp.json`) | Cut to MG | One tick per item, synced to the words. Hold the finished checklist for 3s, because people will screenshot it. |

### 8. Quick test: Shop Manager (9:20 to 10:20)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 9:20 | "Before we build anything, I want to see what a slightly more privileged role gives me..." | SR: claude-ai user, role changed from Subscriber to Shop Manager | Hard cut | Zoom on the dropdown change. Small LT: "Test only". |
| 9:35 | "So now I can ask things like how many orders were processed this week..." | SR: the prompt and Claude's answer | | **Blur customer names, addresses and phone numbers.** Keep the tool-call line (`execute-ability`) visible and highlighted, because it proves the answer came through MCP. |
| 9:50 | "...it shows the padlocks coming off the jars as the role changes..." | MG: kitchen returns and two padlocks drop off | Cut to MG | Reuse the beat 5 art. The padlock "clunk" SFX is fine here. |
| 10:05 | "And I'm putting it straight back to Subscriber afterwards..." | SR: role set back to Subscriber, "User updated" notice | Hard cut | Don't cut this for time. It's the responsible payoff. |

### 9. Guard rails (10:20 to 11:55)

Purpose: pay off the cold-open promise. This is the most distinctive part of the video, so give it room and weight.

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 10:20 | "Now, remember what I said at the start about SSH?" | A, tighter framing than usual | Hard cut, music drops out | Tone shift. Tighter framing signals "this is the serious bit". |
| 10:26 | "I'm using Claude Code, and it will be sneaky unless you give it some guard rails." | A | | |
| 10:32 | "In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove." | SR: the project file tree with the Wordmove `movefile` highlighted | L-cut | Blur hosts and paths inside the file if you open it. Better still, just show the filename. |
| 10:42 | "While I was testing, I asked the agent to do something it couldn't do over MCP..." | A | J-cut | |
| 10:52 | "It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH." | SR: **the real terminal transcript**, slow scroll | Hard cut | **Evidence beat.** Soft-box the actual `ssh` command line. Blur the host, user, IP and key path. Unblur the opening flash from 0:00 here so viewers connect the two. No music. |
| 11:05 | "It went straight round the sandbox I thought it was in." | MG: kitchen, and the chef ignores the hatch and climbs in through the window | Cut to MG | This can be played lightly for the laugh. It releases the tension. |
| 11:12 | "So put the rules in writing..." | A | Hard cut, music back in | |
| 11:22 | "That goes in your project's CLAUDE.md, or your global one." | SR: CLAUDE.md with the rule, highlighted | Wipe to SR | Hold 4s so people can read it. |
| 11:32 | "Then back it up with actual permissions in the hidden .claude folder, in settings.local.json..." | SR: `.claude/settings.local.json` with the deny rules | Hard cut | Highlight the SSH deny entries. Hold 4s. |
| 11:45 | "Instructions are a request, whereas permissions are a wall, so use both. Belt and braces." | MG: two stacked layers, "CLAUDE.md = asks nicely" and "settings deny = actually stops it" | Cut to MG | **Key point.** This is the most screenshot-able frame in the video, so make it clean. Hold 3s. |

### 10. Now the abilities: the slots problem (11:55 to 13:20)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 11:55 | "Right. We're connected, we've got guard rails..." | A | Graphic wipe (optional chapter card "The ability") | Upbeat reset after the serious section. |
| 12:05 | "On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm..." | SR: slot management screen in CasaGees admin | Hard cut | Soft-box the capacity column as "twelve pizzas" is said. |
| 12:25 | "When somebody orders, that slot's capacity drops..." | SR: before and after of a slot's capacity, or a slot showing as full | | Only use real data. If a live example isn't easy, stay on the admin screen. |
| 12:35 | "The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them..." | A | Hard cut | Genuine mild frustration. It's relatable. |
| 12:45 | "And if we forget, nobody can order." | MG: calendar, Thursday to Saturday filling up, then Sunday blank with a "?" | Cut to MG | |
| 12:55 | "So why not expose the slot system to the AI as an ability and let it generate them?" | A | Hard cut | |
| 13:02 | "I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it." | A | | Plays straight to camera. The payoff comes at 14:25. |
| 13:10 | "Then from Claude Cowork I can set up a skill and a schedule... come Sunday morning the slots are already sitting there..." | MG: the same calendar refilling itself on Sunday morning | Cut to MG | The satisfying payoff, so let it animate fully. |
| 13:18 | "Let's build it." | A, then cut straight to the editor | Hard cut on "it" | |

### 11. Confession time: the main plugin file (13:20 to 14:50)

| TC    | Spoken                                                                                                                                                                                           | On screen                                                                                                    | Transition                     | Notes                                                                                             |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------- |
| 13:20 | "Okay, so I'm not going to lie to you. I got AI to build the ability as well."                                                                                                                   | A                                                                                                            | Hard cut from the editor flash | Self-deprecating, so play it with a grin. Small on-screen stamp "Confession" is optional.         |
| 13:28 | "The prompt was something like 'build me an ability using the WP Abilities API to read and update order slots'..."                                                                               | SR or MG: the prompt as a text card                                                                          | Cut                            | Show it as a card with the prompt text, not a fake chat UI.                                       |
| 13:40 | "...walking you through the logic it came up with, which lives in its own separate plugin."                                                                                                      | SR: the plugin folder in the file tree                                                                       | Hard cut                       |                                                                                                   |
| 13:48 | "Let's start with the main plugin file. Up top we've got the usual bits defined..."                                                                                                              | SR: main plugin file, top of the file                                                                        |                                | Soft-box the constants block.                                                                     |
| 14:00 | "Then we register an abilities category. Think of that as the shelf in the cupboard."                                                                                                            | SR: `wp_register_ability_category` call highlighted                                                          |                                | Optional 2s MG insert: the kitchen shelf with the label "casagees". It ties back to the metaphor. |
| 14:15 | "Below that is where the order slots ability gets registered, hooked into the Abilities API."                                                                                                    | SR: scroll to the hook                                                                                       |                                |                                                                                                   |
| 14:25 | "The last thing in here is a function called casagees_abilities_can_manage. That's the permission callback. It checks whether the current user has a capability called manage_casagees_slots..." | SR: zoom on the function, then soft-box `current_user_can( 'manage_casagees_slots' )`                        | Punch-in                       | **Key point.** Burn in `manage_casagees_slots` as a caption.                                      |
| 14:35 | "...given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI..."                                                                                                    | SR: terminal, `wp user add-cap claude-ai manage_casagees_slots` and its success message                      | Hard cut                       | Hold 3s so people can copy it. Blur the host in the prompt.                                       |
| 14:42 | "...so it sits on that one user rather than a whole role. Subscribers, customers and even Shop Managers don't have it..."                                                                        | MG: three greyed-out role badges and one lit-up "claude-ai" badge                                            | Cut to MG                      |                                                                                                   |
| 14:52 | "That's the padlock on the jar, and only one user has the key."                                                                                                                                  | MG: 2s kitchen insert, one padlock clicks onto the "slots" jar and a single key appears labelled "claude-ai" | Cut to MG                      | The padlock is real now, so let it land.                                                          |

### 12. Inside the ability (14:50 to 17:55)

Purpose: the longest single stretch of code. Keep it moving with zooms and highlights, and don't sit on a static editor for more than about 8 seconds.

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 14:50 | "Now for the ability itself. First thing you'll see is an array called the slot schema..." | SR: abilities folder, order slots file, top | Hard cut | |
| 15:02 | "Registering an ability works like this. You give it a namespaced name, something like casagees/get-order-slots..." | SR: zoom on `wp_register_ability( 'casagees/get-order-slots'` | Punch-in | Callout: "namespace/ability-name". |
| 15:15 | "A label, a description, the category we set up a minute ago. Then the two that matter." | SR: soft-box each arg as it's named | | Quick highlight hops, about 1s each. |
| 15:25 | "The execute callback is all of the logic the ability can actually do..." | SR: `execute_callback` highlighted, then a fast scroll through its body | | Speed-scroll the body to show there's a lot there, without reading it. |
| 15:45 | "I'm not going to go through all of this line by line, because it's a video in its own right." | A | Hard cut | A nod to the future video. Optional small card "Full build: coming soon". |
| 15:52 | "The permission callback is the function we just looked at on the other file..." | SR: `permission_callback` line highlighted | Hard cut | |
| 16:02 | "Put simply, we've registered two abilities. One to get the order slots, and one to create them." | MG: two jars, "get-order-slots (read)" and "create-order-slots (write)" | Cut to MG | A clear visual split between read and write. Colour the write jar differently, which quietly supports the permission point. |
| 16:15 | "Let me give you a quick overview of the get ability..." | SR: `input_schema` in the get ability | Hard cut | |
| 16:25 | "The input schema is what the ability expects to be asked. It's the shape of my question..." | SR: highlight the date, availability and limit properties one at a time | | Sync each highlight to its word. |
| 16:45 | "If I ask the AI something that doesn't fit the schema, it knows it can't use this jar." | MG: 2s insert, a mismatched request bouncing off a jar | Cut to MG | Optional. Cut it if the section runs long. |
| 16:50 | "The output schema is the shape of the answer..." | SR: `output_schema` highlighted | Hard cut | |
| 17:05 | "That's really what the Abilities API is about... what it wants, what it gives back, and who's allowed to call it. Sweet huh!" | MG: three-part card, "Input schema / Output schema / Permission callback" | Cut to MG | **Key point** of the whole ability section. It's the second "Sweet huh!", so keep the delivery different from beat 7's. |
| 17:20 | "One more important bit. In the ability's meta there's an mcp array with public set to true. Abilities are private by default..." | SR: the meta array, soft-box `'mcp' => array( 'public' => true )` | Hard cut | Optional 2s MG: a jar sliding from the back of the cupboard onto the front shelf. |
| 17:32 | "Now, although I did get AI to write this, I do understand what it's done..." | A | Hard cut | Honest and relaxed. It's an important credibility beat for an audience wary of AI code. |
| 17:50 | "...maybe I'll come back and do a proper video on the ability itself, because it deserves one." | A | | |

### 13. End screen (17:55 to 18:15, with the end screen running to about 18:20)

| TC | Spoken | On screen | Transition | Notes |
|---|---|---|---|---|
| 17:55 | "If you want the theory behind all this... that's in the video on screen now." | A, framed left. End screen elements on the right: anchor video plus subscribe | Hard cut, end screen elements animate in | The end screen needs at least 5s and can run up to 20s. Point at the video tile as it's mentioned. |
| 18:08 | "And if you've already connected an AI to your site, go and check what role it's running as. Happy building." | A | | Last line straight to camera. Hold 2s after "Happy building" before fading the music. |

---

## Asset list

**Motion graphics (build once, reuse):**
- Chapter card template (1 to 5, plus an optional "The ability")
- Kitchen illustration, layered: wall, hatch, cupboard, jars, padlocks, chef, `.mcp.json` key, window. It gets used in beats 5, 8, 9 and optionally 11.
- Three greyed icons: user, key, plugin
- Data flow: laptop > mcp-wordpress-remote > internet > site with adapter
- Red warning strip for the password line
- Session on and off toggle (optional)
- Five-item recap checklist
- "CLAUDE.md = asks nicely / settings deny = actually stops it" layer graphic
- Calendar animation: filling up, blank Sunday, refilling Sunday
- Two jars, read and write
- Input, output and permission three-part card
- LTs: MCP definition, application password definition, "Test only"

**Screen recordings to capture:**
- wp-admin: add user, role dropdown, application password generation, role change to Shop Manager and back
- GitHub: repo home, Releases page, CLI usage guide config example
- Plugins > Add New > Upload > Activate
- Editor: building `.mcp.json` line by line (record it slowly, because you can always speed it up)
- Terminal: Claude Code launch, MCP approval prompt, "can you see my site" prompt and response, Shop Manager order query with tool calls visible
- The real SSH transcript
- CLAUDE.md rule and `.claude/settings.local.json` deny rules
- CasaGees slot management admin
- The abilities plugin: main file and ability file

**B-roll:**
- Studio app with the AI panel (beat 1)
- CasaGees homepage or real pizza footage (beat 6)

**Blur list:** application password, any env values, SSH host, user, IP and key path, customer personal data, and the production URL if you'd rather not show it.

---

## Updated chapters for the description

These are estimates, so re-stamp them from the final cut. YouTube needs the first chapter at 00:00, at least three chapters, and each one at least 10 seconds long. The v2 script's list is missing the ability walkthrough, so it's added here.

```
00:00 Claude Code got in over SSH
01:04 What MCP is
01:30 Step 1: a Subscriber user
02:25 Step 2: an application password
03:10 Step 3: install the MCP Adapter
04:15 The hatch and the cupboard
05:40 Step 4: the .mcp.json config file
07:55 Step 5: connect Claude Code
09:20 What a Shop Manager role can see
10:20 Guard rails: CLAUDE.md and permissions
11:55 Automating delivery slots with an ability
13:20 The plugin file and permission callback
14:50 Inside the ability: schemas and meta
17:55 What next
```

---

## If it needs to come in shorter

The runtime is about 18 minutes. If you want it nearer 15, trim in this order (roughly how long each saves):

1. **Beat 12, the input and output schema detail** (about 60s). Keep the three-part card and cut the property-by-property highlights.
2. **Beat 7, the global versus project config aside** (about 20s).
3. **Beat 11, the constants and "usual bits" walkthrough** (about 20s).
4. **Beat 1, the Studio aside** (about 15s). It's nice context but not essential.

Don't cut the Subscriber reset (beat 8), the SSH evidence (beat 9) or the "asks nicely / actually stops it" frame. Those three are why this video exists rather than the other twenty.
