# Vimwiki Helpers for SmartThings Tools

I like to keep track of outstanding reviews, tickets, etc. in vimwiki. One
annoyance though is adding those tasks to vimwiki: the links for Atlassian and
Github don't include title information in their URLs, so I'm stuck either
having to enter my own titles or having to open links to remind myself what
they are.

This little script uses the tool APIs to take a URL and return a formatted
vimwiki link that has the URL, type (i.e. Confluence, Github), and title. This
is mapped to a keybinding in vim that reads the current value from my
clipboard so all I have to do to insert the link is copy it from an email,
Slack, etc and hit the keybinding.

The binding can be installed with a vim plugin manager, i.e. for Plug. The
helper script also needs to be on your PATH - I manage these together with
pipx and the Plug `do` command:

```vim
Plug 'nastevens/stvimhelper', { 'do': 'pipx install --force .', 'for': 'vimwiki' }
```

With that inserting a link from the clipboard is bound to <C-L> in insert mode.

## License

Copyright (c) 2021, Nick Stevens <nick@bitcurry.com>

Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
http://www.apache.org/license/LICENSE-2.0> or the MIT license <LICENSE-MIT or
http://opensource.org/licenses/MIT>, at your option. This file may not be
copied, modified, or distributed except according to those terms.
