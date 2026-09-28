# Connect Claude Code to WordPress with MCP (Then Lock It Down)

**Type:** Setup walkthrough, video 1 of the MCP series (the practical companion to the anchor video)
**Previous version:** `claude-code-wordpress-mcp-script.md`
**Source notes:** `wordpress-mcp-content-notes.md`
**vidIQ research:** `wordpress-mcp-and-the-abilities-api-the-official-way-to-connect-ai-to-wordpress.md` (keyword set, competitor table, "Reference videos to watch"), plus the checks on 23 September 2026 below
**Primary keywords:** `wordpress mcp setup`, `wordpress mcp claude`, `connect claude ai to wordpress via mcp`
**Secondary keywords:** `wordpress mcp`, `wordpress mcp adapter`, `claude code wordpress`, `wordpress abilities api`

---

## Optimised titles

Keyword numbers are from the vidIQ research in the anchor video file and the notes (14–15 September 2026), so treat them as directional. On 23 September 2026 there were only enough vidIQ credits to score options 1 and 4 (vidIQ title score, long-form). The credits reset on 27 September if you want the others scored.

1. **Connect Claude Code to WordPress with MCP (Then Lock It Down)** (recommended, **scored 91**)
2. WordPress MCP Setup with Claude Code: The Official Adapter, Step by Step
3. Claude Code Found Another Way Into My WordPress Site (MCP Setup Done Safely)
4. How to Connect Claude AI to WordPress via MCP (Without Giving It Admin) (**scored 86**)
5. WordPress MCP Adapter + Claude Code: Subscriber User, App Password, Done

Option 1 carries "claude", "wordpress" and "mcp" in the first half, and the bracket promises the thing nobody else covers. Option 3 is the strongest curiosity hook (the SSH story) but it's weak on search terms, so save that one for the thumbnail text or a Short rather than the title. Option 4 targets the highest-growth phrase (`connect claude ai to wordpress via mcp`, +240%) almost word for word. Bear in mind that WebSensePro already owns that exact phrase as a title (see "Closest competitor" below), which is another reason to go with option 1.

**Thumbnail text ideas** (three to four words, not a repeat of the title):
- "IT FOUND SSH" with the terminal screenshot blurred behind
- "SUBSCRIBER ONLY" with a padlocked jar
- "LOCK IT DOWN"

---

## Audience brief

I've inferred this from the script rather than asking, so push back if it's off.

**Want to know:** how to connect Claude Code to a live WordPress site; exactly what goes in the `.mcp.json` file; whether it's safe to do on a real site.

**Need to know:** the MCP Adapter isn't on the plugin repo yet; use the lowest role that does the job; keep the application password out of the file; Claude Code will look for other routes into your site if you don't stop it, and instructions alone won't stop it.

**Don't need:** the full three-layer theory (that's the anchor video), the deprecated Automattic plugin history, JWT or OAuth, the "is MCP dead" argument, and the ability build in detail (drop that in after "Let's build it", or split it into its own video).

**Story shape (Hook, Problem, Insight, Action):**
- *Hook:* the AI broke out of the sandbox over SSH (teased in the cold open, paid off later).
- *Problem:* the official docs skip the setup steps and the config file.
- *Insight:* the key to the hatch is the local config, and permissions are the padlocks on the jars.
- *Action:* five steps, guard rails, then build a real ability for the CasaGees slots.

---

## Script

Bracketed lines are on-screen cues, not narration. `[MG]` marks a motion graphic.

### Cold open

[Talking head]

[MG: quick flash of the terminal where Claude reaches for SSH, blurred, with a red "ACCESS" stamp. Hold for two seconds.]

While I was testing this, Claude Code got into my live WordPress site over SSH, which is not how I'd told it to get in. I'll show you exactly how that happened later, and how to stop it happening to you.

Okay, so some of you are going to hate this. AI is everywhere, and we're using it in WordPress in all sorts of different ways now. Locally, you can spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI. Fine. But I wanted to set up my own configuration, using Claude Code, talking to a real site.

Now, there is official documentation for this. It lives on the WordPress GitHub account under the MCP Adapter repository, and it tells you how to connect your site over MCP. What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file. So that's what this video is.

For those of you who don't know, MCP stands for Model Context Protocol, and all it really is is a standard way for an AI agent to talk to a piece of software. Keep that in your back pocket, because I'll give you a better analogy in a minute.

[MG: lower third, "MCP = Model Context Protocol. A standard way for AI to talk to software."]

### Step one: a user with the lowest possible role

[Screen: production site wp-admin, Users > Add New]

[MG: chapter card, "1. The user"]

The first thing to do happens on your live production site, not your local one, because we're going to connect local to production and interrogate the real thing. So on your live site, create a new user. I've called mine claude-ai, and I've given it a password I'm probably never going to log in with (which doesn't matter for this connection anyway).

The important bit is the role. Set it to the lowest possible, which is Subscriber. A lot of the tutorials out there just generate the password on the admin account they're already logged in as, and you really don't want to hand an AI admin and let it go wild on your site doing things you didn't expect.

[Zoom: role dropdown set to Subscriber]

### Step two: an application password

[Screen: user profile, Application Passwords section]

[MG: chapter card, "2. The application password"]

Next, on that same user, scroll down to Application Passwords and generate one. If you've not come across these, an application password is a separate credential that lets a piece of software talk to your site without using your actual login. Give it a name, hit the button, and WordPress generates it for you and shows it once, so copy it somewhere safe because you won't see it again.

[Blur the generated password in post]

So now we've got a username and an application password for our claude-ai user. On their own, they don't give an AI anything useful to work with. They just sit there.

### Step three: install the MCP Adapter

[Screen: GitHub, WordPress/mcp-adapter repo, then terminal]

[MG: chapter card, "3. The MCP Adapter"]

Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory, but at the moment it doesn't live there. It lives on GitHub under the official WordPress account, in a repo called `mcp-adapter`, and the link is in the description.

[Screen: GitHub Releases page, download mcp-adapter.zip]

The easiest way in is the Releases page on that repo, where there's a ready-made `mcp-adapter.zip` to download. Upload that through Plugins, Add New, on your live site, and activate it. (If you'd rather build it yourself, you can clone the repo and build the zip, but for a live site I'd stick with the tagged release.)

[MG: three icons appear one at a time (user, key, plugin), each greyed out]

Again, on its own, it just sits there. A user with an application password does nothing, and having the adapter installed does nothing. The magic is in how you put them together, and that's where the analogy comes in.

### The hatch and the cupboard

[Talking head]

[MG: illustrated kitchen. A hatch in the wall, a cupboard of jars behind it, some jars padlocked. Build it up as the lines land.]

Imagine you're a chef (bear with me, I was one once) and you need to get into the ingredients cupboard. The MCP server is the doorway into that cupboard. The hatch, if you like.

Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API. An ability is a single thing your site can do, described in a way an AI agent can understand, like creating a post, looking up an order or regenerating delivery slots. Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check, much like the capabilities your user roles already have.

So some jars have a padlock on them and some are open, depending on who's asking. Our subscriber user can't reach much, whereas an admin could reach a lot more. That's the whole point of picking the lowest role.

[MG: a key appears on the chef's side of the hatch, labelled ".mcp.json"]

What you really need to understand is that the key to the hatch is not the adapter plugin, and it's not the user with the application password. The key is the MCP configuration on your local machine. That config is what opens the hatch, and the abilities are what's on the shelves once you're in.

### Step four: the MCP config file

[Screen: editor, project root, new file .mcp.json]

[MG: chapter card, "4. The config file"]

The official docs give you a basic config, but they don't tell you where it lives or how to build it, so let's do that. In your local project folder, create a file called `.mcp.json`, which is just a JSON object.

From the MCP adapter GitHub docs, you can just copy this object directly into your .mcp.json file.

At the top level we need an `mcpServers` object. You can set up multiple servers in here, but this is the bare minimum. Inside that, create an object named after the connection. I've called mine `claude-ai` to match the user.

[Type each line as it's described. Highlight each key as it's mentioned.]

Now the guts of it. `command` is `npx`, and `args` is an array with `-y` and then `@automattic/mcp-wordpress-remote@latest`. That's the little bridge that runs on your machine and talks to the adapter on your site.

[MG: simple flow, laptop > "mcp-wordpress-remote" > internet > site with adapter]

Then the environment variables. `WP_API_URL` is your site, followed by the route to the hatch, which is `/wp-json/mcp/mcp-adapter-default-server`. That's the address the agent goes looking for. I'm using the CasaGees site, which is the pizza delivery service we run from home, a little side hustle that keeps me busy at weekends.

`WP_API_USERNAME` is the user you created, and `WP_API_PASSWORD` is the application password WordPress generated for it.

[Screen: the finished .mcp.json with ${} variables]

Now, for security reasons, I haven't pasted the real values in here. I've set them as environment variables on my machine and I'm referencing them with a dollar sign and the variable name in curly brackets. That way the actual password never ends up in a file that could accidentally get committed. Please don't be the numpty who pushes an application password to GitHub.

[MG: red warning strip, "Never commit real passwords. Add .mcp.json to .gitignore if in doubt."]

Finally, and just for sanity, there's `LOG_FILE`. Point it at a subfolder of your project. Mine goes to `mcp/logs/mcp-production.log`, and when something goes wrong (and it will), that's where you look.

```json
{
  "mcpServers": {
    "claude-ai": {
      "command": "npx",
      "args": ["-y", "@automattic/mcp-wordpress-remote@latest"],
      "env": {
        "WP_API_URL": "https://your-site.com/wp-json/mcp/mcp-adapter-default-server",
        "WP_API_USERNAME": "${WP_API_USERNAME}",
        "WP_API_PASSWORD": "${WP_API_PASSWORD}",
        "LOG_FILE": "./mcp/logs/mcp-production.log"
      }
    }
  }
}
```

[Hold the finished file on screen for at least four seconds so people can pause and copy it]

### Step five: fire it up

[Screen: terminal, start Claude Code in the project]

[MG: chapter card, "5. Connect"]

With that in place, start a Claude Code session in the project. The first thing it'll do is ask whether you want to use this MCP server, so say yes.

You could add this to your global Claude configuration so it's available everywhere, but I don't want that. I want the control to sit inside the project, and I only want this server running while I'm actually in the session. When I close the session, the connection closes with it, and that's a deliberate choice.

Now let's try it. I'm just going to ask the agent, "can you see my site over MCP?"

[Screen: Claude's response with site info. Zoom on the site name.]

And there you go. It comes back with information about the site, so I can confirm it's all connected and running. Sweet huh!

[MG: checklist builds on screen as each item is read]

So, to recap what you actually need: a live site somewhere, a user on it with the minimum role, an application password for that user, and the official MCP Adapter plugin installed. Then in your local project folder, a `.mcp.json` with the `mcpServers` object and an entry for your connection. That's it.

### Quick test: what can it actually see?

[Screen: change claude-ai user role to Shop Manager]

Before we build anything, I want to see what a slightly more privileged role gives me. CasaGees runs on WooCommerce, so I'm going to bump the claude-ai user up from Subscriber to Shop Manager and see what comes back.

[Screen: asking Claude about this week's orders and upcoming orders]

[MG: back to the kitchen. Two padlocks drop off the jars.]

So now I can ask things like how many orders were processed this week, or what orders are coming up, and that kind of works. Granted, it's only reading, but it shows the padlocks coming off the jars as the role changes, which is exactly what you'd expect.

[Screen: switch the role back to Subscriber]

And I'm putting it straight back to Subscriber afterwards, because I only needed it for the test.

### Put the guard rails up first

[Talking head, serious for a second]

Now, remember what I said at the start about SSH? Before I create an ability, I need to show you that, because I found it out the hard way.

I'm using Claude Code, and it will be sneaky unless you give it some guard rails. In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove. While I was testing, I asked the agent to do something it couldn't do over MCP, because I hadn't created the abilities for it yet. So it went looking for another way in. It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH. It went straight round the sandbox I thought it was in.

[Screen: the real terminal transcript of the SSH attempt, key details blurred]

[MG: the kitchen again. The chef ignores the hatch and climbs in through the window.]

So put the rules in writing. Tell the AI, in plain language, that when it's interacting with this site it must only use the MCP connection and the Abilities API, with no SSH and no other route in. That goes in your project's `CLAUDE.md`, or your global one.

[Screen: CLAUDE.md with the rule]

Then back it up with actual permissions in the hidden `.claude` folder, in `settings.local.json`, where you can deny things like SSH commands outright. Instructions are a request, whereas permissions are a wall, so use both. Belt and braces.

[Screen: .claude/settings.local.json with the deny rules]

[MG: two layers, "CLAUDE.md = asks nicely", "settings deny = actually stops it"]

### Now the abilities

[Screen: slot management in the CasaGees admin]

Right. We're connected, we've got guard rails, and apart from what WordPress and WooCommerce already expose, we've got nothing of our own in the cupboard. So let's set some up.

On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm, and we can only do twelve pizzas in any half-hour slot. When somebody orders, that slot's capacity drops so we never over-commit, and if there are no slots left, nobody can order. That's the guard rail for customers.

The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them for next week, every single week. And if we forget, nobody can order.

[MG: calendar, Thursday to Saturday columns filling up, then going blank on Sunday with a "?"]

So why not expose the slot system to the AI as an ability and let it generate them? I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it. Then from Claude Cowork I can set up a skill and a schedule. I do my shifts at the weekend, and come Sunday morning the slots are already sitting there ready for customers, without me having to think about it.

[MG: the same calendar refilling itself on Sunday morning]

[Cut to building the ability]

Let's build it.

[Screen: the abilities plugin open in the editor, main plugin file]

## Confession time: I got AI to build the ability too

Okay, so I'm not going to lie to you. I got AI to build the ability as well. The prompt was something like "build me an ability using the WP Abilities API to read and update order slots", and it went off and built it for me. So what I'm doing here is walking you through the logic it came up with, which lives in its own separate plugin.

Let's start with the main plugin file. Up top we've got the usual bits defined, the version and the plugin directory. Then we register an abilities category. Think of that as the shelf in the cupboard. Every ability I add to this site from now on goes on that shelf, so as the list grows it stays organised.

Below that is where the order slots ability gets registered, hooked into the Abilities API. The ability itself isn't in this file though. It lives in a separate folder called abilities, and we'll have a look at that in a second.

The last thing in here is a function called `casagees_abilities_can_manage`. That's the permission callback. It checks whether the current user has a capability called `manage_casagees_slots`, which I've made up for this plugin and given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI (`wp user add-cap claude-ai manage_casagees_slots`), so it sits on that one user rather than a whole role. Subscribers, customers and even Shop Managers don't have it, so they can't run the ability. That's the padlock on the jar, and only one user has the key.

[Screen: the abilities folder, order slots ability file]

## Inside the ability

Now for the ability itself. First thing you'll see is an array called the slot schema, which is what we'll hand to the Abilities API when we register.

Registering an ability works like this. You give it a namespaced name, something like `casagees/get-order-slots`, and then an array of arguments. Most of them are self-explanatory. A label, a description, the category we set up a minute ago. Then the two that matter.

The execute callback is all of the logic the ability can actually do. In this case it's interrogating the database, working out what slots exist, and taking in any parameters the AI has passed along so it's got something to reason with. I'm not going to go through all of this line by line, because it's a video in its own right.

The permission callback is the function we just looked at on the other file, `casagees_abilities_can_manage`. Same padlock, wired in here.

Put simply, we've registered two abilities. One to get the order slots, and one to create them. One goes and fetches the data, the other one writes it.

[Screen: input_schema and output_schema in the get ability]

Let me give you a quick overview of the get ability, because there are two parts we've not covered yet.

The input schema is what the ability expects to be asked. It's the shape of my question, if you like. Things like dates, whether I'm asking about availability, any limits on how much to return. If I ask the AI something that doesn't fit the schema, it knows it can't use this jar.

The output schema is the shape of the answer. The AI takes my input, runs the ability, and gets structured data back that it already knows how to read. That's really what the Abilities API is about. Not just "here's a function", but "here's what it wants, here's what it gives back, and here's who's allowed to call it". Sweet huh!

[Screen: the meta array, `'mcp' => array( 'public' => true )` highlighted]

One more important bit. In the ability's meta there's an `mcp` array with `public` set to true. Abilities are private by default, so without that the ability is registered but the MCP Adapter won't expose it, and your AI will never see the jar on the shelf. Easy one to miss.

[Talking head]

Now, although I did get AI to write this, I do understand what it's done, because I know how the Abilities API works. It'll look slightly different for anyone else who writes this logic, or gives it a different prompt, but for my prompt it did a pretty good job and I'm happy to leave it as it is. I trust it. Like I said, maybe I'll come back and do a proper video on the ability itself, because it deserves one.

### End screen

[Talking head, last 20 seconds, end screen elements on the right]

If you want the theory behind all this (what the Abilities API actually is and why the official adapter matters), that's in the video on screen now. And if you've already connected an AI to your site, go and check what role it's running as. Happy building.

---

## Metadata

**Title**

Connect Claude Code to WordPress with MCP (Then Lock It Down)

**Description**

Connect Claude Code to a live WordPress site using the official WordPress MCP Adapter, a Subscriber-level user and an application password. Then lock it down, because while I was testing this, Claude Code went round MCP and got into my site over SSH.

The official docs tell you how to connect over MCP but skip the setup. This video walks through it properly: creating a low-privilege user, generating an application password, installing the MCP Adapter from GitHub, building the `.mcp.json` config file with environment variables, and testing the connection. Then I show how the user role changes what the AI can see, how to put guard rails in place with CLAUDE.md and Claude Code permissions, and how I'm using the Abilities API to automate delivery slots on a real WooCommerce site.

Chapters:
00:00 Claude Code got in over SSH
00:00 What MCP is
00:00 Step 1: a Subscriber user
00:00 Step 2: an application password
00:00 Step 3: install the MCP Adapter
00:00 The hatch and the cupboard
00:00 Step 4: the .mcp.json config file
00:00 Step 5: connect Claude Code
00:00 What a Shop Manager role can see
00:00 Guard rails: CLAUDE.md and permissions
00:00 Building an ability for delivery slots

The config file from the video:
(paste the JSON block from the script here, or link to a Gist)

Links:
- WordPress MCP Adapter: https://github.com/WordPress/mcp-adapter
- Abilities API in WordPress 6.9: https://make.wordpress.org/core/2025/11/10/abilities-api-in-wordpress-6-9/
- Introducing the WordPress MCP Adapter: https://developer.wordpress.org/news/2026/02/from-abilities-to-ai-agents-introducing-the-wordpress-mcp-adapter/
- Claude Code MCP docs: https://docs.claude.com/en/docs/claude-code/mcp
- Claude Code permissions: https://docs.claude.com/en/docs/claude-code/settings

Square One Software: https://squareone.software

**Tags** (under YouTube's 500-character limit)

wordpress mcp setup, wordpress mcp claude, connect claude ai to wordpress via mcp, wordpress mcp, claude code wordpress, wordpress mcp adapter, mcp wordpress, wordpress abilities api, claude code mcp, mcp json, wordpress application password, wordpress ai agent, model context protocol wordpress, woocommerce mcp, claude code, wordpress development

**Hashtags**

#WordPress #ClaudeCode #MCP #WordPressDevelopment #WooCommerce

**Pinned comment**

What role is your AI running as on your site? If the answer is "admin" or "I don't know", that's your weekend sorted. Config file is in the description.

---

## Closest competitor (checked 23 September 2026)

The anchor file's research lists every big video as running on a third-party plugin, and it flagged three unverified videos from search. I checked them with vidIQ, and one of them changes the pitch.

| Video | Channel | Views | Published | What it actually does |
|---|---|---|---|---|
| How To Connect Claude AI to WordPress via MCP (Step-by-step) | WebSensePro | 13,512 | 8 Jun 2026 | **Uses the official MCP Adapter** (from Releases) plus the presenter's own `wsp-wordpress-mcp` plugin, with Claude Desktop |
| It's Official: You Can Now Use Claude with WordPress! | WordPress.com | 119,557 | 18 Feb 2026 | The WordPress.com Claude connector. No adapter, no self-hosted setup |
| I Gave Claude Code 90 Minutes with WordPress | Techies Reviews | 237 | 20 May 2026 | WordPress Agent Skills in Studio and Cursor. Not an MCP setup video |

So the line "nobody uses the official adapter" (in the anchor script and the notes) is no longer true, and shouldn't go in either video. What v2 has that WebSensePro doesn't is still plenty. From the transcript, that video generates the application password on the only user on the site (the admin), clicks "always allow" on every tool call, switches on create, update and delete abilities for posts, pages, users and media, and has Claude trash a post as a demo. There's no dedicated user, no lowest role, no environment variables, no guard rails and no Claude Code. In other words, it's the exact setup this video warns against, so it's a useful reference if you want a "don't do this" example (without naming names, ideally).

Its "Set Abilities & Permissions" chapter is a settings screen in the third-party plugin, not the permission callbacks in the Abilities API. That's worth a sentence in the anchor video, because viewers will conflate the two.

## What changed from v1

- Cold open now leads with the SSH story as a tease, then pays it off in the guard rails section. That's the one thing no competing video has, so it earns the first ten seconds.
- Added chapter cards, motion graphic cues, blur and hold cues, and an end screen.
- Added a line switching the role back to Subscriber after the Shop Manager test. Otherwise the video ends with a Shop Manager AI user on a live shop, which undercuts the whole message.
- Fixed "public SSH keys" (see fact checks below).
- Rewrote "every action you can take in the WordPress backend is effectively an ability" and "we've got no abilities" (see fact checks below).
- Light tidy of stacked short sentences to match the voice guide. The substance and jokes are unchanged.

## Fact-check flags before filming

- **SSH keys.** v1 said Claude "found my public SSH keys". SSH logs in with your *private* key (the public one sits on the server), so that line would get picked apart in the comments. v2 says it "used the SSH keys already set up on my machine", which is accurate either way.
- **"Every action is effectively an ability."** Not true. Abilities only exist if core, a plugin or you register them, and the default MCP server only exposes the ones flagged as public for MCP. v2 says nothing is in the cupboard unless it's registered.
- **"We've got no abilities" vs the demos.** The "can you see my site?" answer and the WooCommerce order questions both worked, so *something* was exposed (WordPress 6.9 core abilities, and presumably WooCommerce's own). Check what `discover-abilities` actually lists before filming so the "we've got nothing" line is honest. v2 hedges it to "apart from what WordPress and WooCommerce already expose".
- **Building the plugin zip.** Resolved. There is a ready-made zip on the Releases page (`v0.6.1`, published 13 August 2026, asset `mcp-adapter.zip`), so Step three now points there instead of cloning. Check it's still the latest release on the day you film.
- **`WP_API_URL` format.** v2 is right: the adapter's own CLI usage guide (`docs/guides/cli-usage.md`) uses the full `/wp-json/mcp/mcp-adapter-default-server` path. The anchor script says "bare domain, no path", which is wrong and needs fixing before that one is filmed.
- **Plugin directory status.** "Being assessed for the plugin directory" is hearsay unless you've got a source. v2 softens it to "as far as I know". Link a Trac ticket or Make post if you have one.
- **`${VAR}` in `.mcp.json`.** Claude Code does support environment variable expansion in `.mcp.json`, but the variables have to be set in the shell that launches Claude Code. Worth a one-line mention on screen, because that's the first thing people will get wrong.
- **Shop Manager reading orders.** Confirm this came through MCP abilities and not the agent falling back to something else (given the SSH story, viewers will ask). Show the tool call in the Claude Code output.
- **Show the SSH transcript.** Same as v1: it's a strong claim, so it needs to be on screen.
