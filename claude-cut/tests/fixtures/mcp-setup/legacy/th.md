While I was testing this, Claude Code got into my live WordPress site over SSH, which is not how I'd told it to get in. I'll show you exactly how that happened later, and how to stop it happening to you.

Okay, so some of you are going to hate this. AI is everywhere, and we're using it in WordPress in all sorts of different ways now. Locally, you can spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI. Fine. But I wanted to set up my own configuration, using Claude Code, talking to a real site.

Now, there is official documentation for this. It lives on the WordPress GitHub account under the MCP Adapter repository, and it tells you how to connect your site over MCP. What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file. So that's what this video is.

For those of you who don't know, MCP stands for Model Context Protocol, and all it really is is a standard way for an AI agent to talk to a piece of software. Keep that in your back pocket, because I'll give you a better analogy in a minute.

## Step one: a user with the lowest possible role

A lot of the tutorials out there just generate the password on the admin account they're already logged in as, and you really don't want to hand an AI admin and let it go wild on your site doing things you didn't expect.

## Step two: an application password

So now we've got a username and an application password for our claude-ai user. On their own, they don't give an AI anything useful to work with. They just sit there.

## Step three: install the MCP Adapter

The magic is in how you put them together, and that's where the analogy comes in.

## The hatch and the cupboard

Imagine you're a chef (bear with me, I was one once) and you need to get into the ingredients cupboard. The MCP server is the doorway into that cupboard. The hatch, if you like.

What you really need to understand is that the key to the hatch is not the adapter plugin, and it's not the user with the application password.

## Step four: the MCP config file

I'm using the CasaGees site, which is the pizza delivery service we run from home, a little side hustle that keeps me busy at weekends.

Please don't be the numpty who pushes an application password to GitHub.

## Step five: fire it up

You could add this to your global Claude configuration so it's available everywhere, but I don't want that. I want the control to sit inside the project, and I only want this server running while I'm actually in the session. When I close the session, the connection closes with it, and that's a deliberate choice.

## Put the guard rails up first

Now, remember what I said at the start about SSH? Before I create an ability, I need to show you that, because I found it out the hard way.

I'm using Claude Code, and it will be sneaky unless you give it some guard rails. In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove. While I was testing, I asked the agent to do something it couldn't do over MCP, because I hadn't created the abilities for it yet. So it went looking for another way in. It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH. It went straight round the sandbox I thought it was in.

So put the rules in writing. Tell the AI, in plain language, that when it's interacting with this site it must only use the MCP connection and the Abilities API, with no SSH and no other route in.

## Now the abilities

Right. We're connected, we've got guard rails, and apart from what WordPress and WooCommerce already expose, we've got nothing of our own in the cupboard. So let's set some up.

The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them for next week, every single week. And if we forget, nobody can order.

So why not expose the slot system to the AI as an ability and let it generate them? I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it.

Let's build it.

## Confession time: I got AI to build the ability too

Okay, so I'm not going to lie to you. I got AI to build the ability as well. The prompt was something like "build me an ability using the WP Abilities API to read and update order slots", and it went off and built it for me. So what I'm doing here is walking you through the logic it came up with, which lives in its own separate plugin.

## Inside the ability

I'm not going to go through all of this line by line, because it's a video in its own right.

Now, although I did get AI to write this, I do understand what it's done, because I know how the Abilities API works. It'll look slightly different for anyone else who writes this logic, or gives it a different prompt, but for my prompt it did a pretty good job and I'm happy to leave it as it is. I trust it. Like I said, maybe I'll come back and do a proper video on the ability itself, because it deserves one.

## End screen

Now, I know there are a multitude of ways to connect an MCP server to your WordPress site, whether that's through Studio or through Claude Code. But this is the official WordPress way of doing it, and that's why I'm interested.

So, over to you. Have you built anything using this method? Have you registered any of your own abilities with the Abilities API? I'd love to know whether people are actually using it day to day, or whether it's just the big players for now. I'm using it, and I like it quite a bit!

Anyway, thanks so much for watching. If you liked this video, please give it a like, as it helps other people find this content. And if you want to see something else, check out this video here _(point to end screen)_.

Thanks for watching, and I'll see you in the next one.