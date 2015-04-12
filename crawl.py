#!/usr/bin/env python
import debug

import okcupyd

u = okcupyd.User.from_credentials("okminerva0", "okminerva")
p = u.quickmatch() # p is an instance of the Profile class

dump(p)

print('Profile of {0}'.format(p.username))
