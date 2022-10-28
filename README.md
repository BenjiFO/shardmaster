# shardmaster
***This is ALPHA-stage software; some feature may be missing, and the documentation may be lacking or not fully represent the current state of the code.***

SHARDMASTER is an OSINT automation library for small-scale data gathering tasks. It allows to _shard_ (run distributedly) and _schedule_ series of tasks over multiple _workers_ each having a _persona_, and aims at abstracting away the logic needed to do so. 

This is useful if you need multiple channels to parallelize the data gathering tasks over: for instance, if you need to use multiple Facebook accounts at the same time, or to go through multiple IPs in order to avoid getting rate-limited. 

Technically, the workers are corountine-based agents, each one having a persona that embodies its identity; and thus may provide input on _how_ it will perform its tasks (again: likely an IP address to use as proxy, or maybe the account to use to make some requests to a platform's API). 

The most important piece of code you will need to provide is the _executor_: that which runs inside the worker, receives a task, and performs it. The logic of scheduling, of task distribution, etc is in SHARDMASTER; you have to provide it parameters, that's all. 

## Documentation
TBW

## Getting started
TBW