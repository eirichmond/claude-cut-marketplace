# Voiceover: Connect Claude Code to WordPress with MCP

## Step one: a user with the lowest possible role

**VO-01**

The first thing to do happens on your live production site, not your local one, because we're going to connect local to production and interrogate the real thing. So on your live site, create a new user. I've called mine claude-ai, and I've given it a password I'm probably never going to log in with (which doesn't matter for this connection anyway).

**VO-02**

The important bit is the role. Set it to the lowest possible, which is Subscriber.

## Step two: an application password

**VO-03**

Next, on that same user, scroll down to Application Passwords and generate one. If you've not come across these, an application password is a separate credential that lets a piece of software talk to your site without using your actual login. Give it a name, hit the button, and WordPress generates it for you and shows it once, so copy it somewhere safe because you won't see it again.

## Step three: install the MCP Adapter

**VO-04**

Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory, but at the moment it doesn't live there. It lives on GitHub under the official WordPress account, in a repo called mcp-adapter, and the link is in the description.

**VO-05**

The easiest way in is the Releases page on that repo, where there's a ready-made mcp-adapter.zip to download. Upload that through Plugins, Add New, on your live site, and activate it. (If you'd rather build it yourself, you can clone the repo and build the zip, but for a live site I'd stick with the tagged release.)

**VO-06**

Again, on its own, it just sits there. A user with an application password does nothing, and having the adapter installed does nothing.

## The hatch and the cupboard

**VO-07**

Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API. An ability is a single thing your site can do, described in a way an AI agent can understand, like creating a post, looking up an order or regenerating delivery slots. Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check, much like the capabilities your user roles already have.

**VO-08**

So some jars have a padlock on them and some are open, depending on who's asking. Our subscriber user can't reach much, whereas an admin could reach a lot more. That's the whole point of picking the lowest role.

**VO-09**

The key is the MCP configuration on your local machine. That config is what opens the hatch, and the abilities are what's on the shelves once you're in.

## Step four: the MCP config file

**VO-10**

The official docs give you a basic config, but they don't tell you where it lives or how to build it, so let's do that. In your local project folder, create a file called .mcp.json, which is just a JSON object.

**VO-11**

From the MCP adapter GitHub docs, you can just copy this object directly into your .mcp.json file.

**VO-12**

At the top level we need an mcpServers object. You can set up multiple servers in here, but this is the bare minimum. Inside that, create an object named after the connection. I've called mine claude-ai to match the user.

**VO-13**

Now the guts of it. command is npx, and args is an array with -y and then @automattic/mcp-wordpress-remote@latest.

**VO-14**

That's the little bridge that runs on your machine and talks to the adapter on your site.

**VO-15**

Then the environment variables. WP_API_URL is your site, followed by the route to the hatch, which is /wp-json/mcp/mcp-adapter-default-server. That's the address the agent goes looking for.

**VO-16**

WP_API_USERNAME is the user you created, and WP_API_PASSWORD is the application password WordPress generated for it.

**VO-17**

Now, for security reasons, I haven't pasted the real values in here. I've set them as environment variables on my machine and I'm referencing them with a dollar sign and the variable name in curly brackets. That way the actual password never ends up in a file that could accidentally get committed.

**VO-18**

Finally, and just for sanity, there's LOG_FILE. Point it at a subfolder of your project. Mine goes to mcp/logs/mcp-production.log, and when something goes wrong (and it will), that's where you look.

## Step five: fire it up

**VO-19**

With that in place, start a Claude Code session in the project. The first thing it'll do is ask whether you want to use this MCP server, so say yes.

**VO-20**

Now let's try it. I'm just going to ask the agent, "can you see my site over MCP?"

**VO-21**

And there you go. It comes back with information about the site, so I can confirm it's all connected and running. Sweet huh!

**VO-22**

So, to recap what you actually need: a live site somewhere, a user on it with the minimum role, an application password for that user, and the official MCP Adapter plugin installed. Then in your local project folder, a .mcp.json with the mcpServers object and an entry for your connection. That's it.

## Quick test: what can it actually see?

**VO-23**

Before we build anything, I want to see what a slightly more privileged role gives me. CasaGees runs on WooCommerce, so I'm going to bump the claude-ai user up from Subscriber to Shop Manager and see what comes back.

**VO-24**

So now I can ask things like how many orders were processed this week, or what orders are coming up, and that kind of works. Granted, it's only reading, but it shows the padlocks coming off the jars as the role changes, which is exactly what you'd expect.

**VO-25**

And I'm putting it straight back to Subscriber afterwards, because I only needed it for the test.

## Put the guard rails up first

**VO-26**

That goes in your project's CLAUDE.md, or your global one.

**VO-27**

Then back it up with actual permissions in the hidden .claude folder, in settings.local.json, where you can deny things like SSH commands outright. Instructions are a request, whereas permissions are a wall, so use both. Belt and braces.

## Now the abilities

**VO-28**

On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm, and we can only do twelve pizzas in any half-hour slot. When somebody orders, that slot's capacity drops so we never over-commit, and if there are no slots left, nobody can order. That's the guard rail for customers.

**VO-29**

Then from Claude Cowork I can set up a skill and a schedule. I do my shifts at the weekend, and come Sunday morning the slots are already sitting there ready for customers, without me having to think about it.

## Confession time: I got AI to build the ability too

**VO-30**

Let's start with the main plugin file. Up top we've got the usual bits defined, the version and the plugin directory. Then we register an abilities category. Think of that as the shelf in the cupboard. Every ability I add to this site from now on goes on that shelf, so as the list grows it stays organised.

**VO-31**

Below that is where the order slots ability gets registered, hooked into the Abilities API. The ability itself isn't in this file though. It lives in a separate folder called abilities, and we'll have a look at that in a second.

**VO-32**

The last thing in here is a function called casagees_abilities_can_manage. That's the permission callback. It checks whether the current user has a capability called manage_casagees_slots, which I've made up for this plugin and given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI (wp user add-cap claude-ai manage_casagees_slots), so it sits on that one user rather than a whole role. Subscribers, customers and even Shop Managers don't have it, so they can't run the ability. That's the padlock on the jar, and only one user has the key.

## Inside the ability

**VO-33**

Now for the ability itself. First thing you'll see is an array called the slot schema, which is what we'll hand to the Abilities API when we register.

**VO-34**

Registering an ability works like this. You give it a namespaced name, something like casagees/get-order-slots, and then an array of arguments. Most of them are self-explanatory. A label, a description, the category we set up a minute ago. Then the two that matter.

**VO-35**

The execute callback is all of the logic the ability can actually do. In this case it's interrogating the database, working out what slots exist, and taking in any parameters the AI has passed along so it's got something to reason with.

**VO-36**

The permission callback is the function we just looked at on the other file, casagees_abilities_can_manage. Same padlock, wired in here.

**VO-37**

Put simply, we've registered two abilities. One to get the order slots, and one to create them. One goes and fetches the data, the other one writes it.

**VO-38**

Let me give you a quick overview of the get ability, because there are two parts we've not covered yet.

**VO-39**

The input schema is what the ability expects to be asked. It's the shape of my question, if you like. Things like dates, whether I'm asking about availability, any limits on how much to return. If I ask the AI something that doesn't fit the schema, it knows it can't use this jar.

**VO-40**

The output schema is the shape of the answer. The AI takes my input, runs the ability, and gets structured data back that it already knows how to read. That's really what the Abilities API is about. Not just "here's a function", but "here's what it wants, here's what it gives back, and here's who's allowed to call it". Sweet huh!

**VO-41**

One more important bit. In the ability's meta there's an mcp array with public set to true. Abilities are private by default, so without that the ability is registered but the MCP Adapter won't expose it, and your AI will never see the jar on the shelf. Easy one to miss.
