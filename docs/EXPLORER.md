# Explorer: connecting Northeastern's cluster

> **Not on the critical path.** On 2026-10-29 the project moved to Azure for everything (see [AZURE.md](AZURE.md)). This guide is kept in case Explorer's free GPUs are useful later, for example to run an open-weight model in bulk. Nothing in the pipeline needs it today.

Explorer is Northeastern's research cluster, with H200, A100, V100, and T4 GPUs. Replace `<user>` with your Northeastern username and `<key>` with the key file name Research Computing (RC) gives you.

**Status on 2026-10-29:** the SSH key works and Claude Code can log in, but the account has no Slurm association, so every `srun` fails. See "If every `srun` fails" below.

---

## Connect Explorer to Claude Code

### Why

Running a model on Explorer means many round trips to the cluster: starting the model server, test runs, and copying results back. Claude Code can do these itself once it can log in without a password prompt.

### Deadline

From **November 6, 2026 at 9 a.m.**, Explorer only accepts SSH with keys that RC generates. Northeastern passwords stop working for SSH then. Set up the keys now. See [SSH instructions for Explorer](https://rc.northeastern.edu/2026/10/23/ssh-instructions-for-explorer/).

### Steps, done once by you

RC generates your key pair in your Explorer home folder: `/home/<user>/.ssh/<user>-<timestamp>` is the private key, and the same name with `.pub` is the public key. Get both onto your Mac by either route below.

1. **Option A, from your Mac's Terminal (recommended).** This copies the keys straight into `~/.ssh`. It works until November 6, while passwords are still accepted.
   ```bash
   # Check the keys exist. Asks for your password and Duo; type "yes" if asked to trust the host key.
   ssh <user>@login.explorer.northeastern.edu 'ls -la ~/.ssh'

   # Copy both key files into ~/.ssh on your Mac
   scp '<user>@login.explorer.northeastern.edu:~/.ssh/<user>-*' ~/.ssh/
   ```

   **Option B, through the Open OnDemand File Browser.**
   - Sign in at https://ood.explorer.northeastern.edu and open **Files**, then **Home Directory**.
   - `.ssh` is a hidden folder. Tick **Show Dotfiles**, then click **Refresh**. A line like "Showing 4 of 19 rows" means hidden items are still not displayed.
   - If it still doesn't appear, click **Change directory**, type `/home/<user>/.ssh`, and press Enter.
   - Tick both `<user>-<timestamp>` files and click **Download**.
   - Move them from Downloads into `~/.ssh` yourself, because Claude Code can't read your Downloads folder:
     ```bash
     mv ~/Downloads/<key> ~/Downloads/<key>.pub ~/.ssh/
     ```

   **If there are no `<user>-*` files** in `~/.ssh` on Explorer, RC hasn't generated your keys yet. Email rchelp@northeastern.edu and ask for your Explorer SSH keys, mentioning the November 6 key requirement.

2. **Lock down the permissions, then authorize the key.** RC generates the key pair, but the server doesn't accept it until the public key is in your `~/.ssh/authorized_keys` on Explorer. `ssh-copy-id` asks for your password once and adds it.
   ```bash
   chmod 600 ~/.ssh/<key>
   chmod 644 ~/.ssh/<key>.pub
   ssh-copy-id -i ~/.ssh/<key>.pub <user>@login.explorer.northeastern.edu
   ```
   If `ssh-copy-id` isn't available, run this on the cluster instead: `cat ~/.ssh/<key>.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`.

3. **Log in once from your own Terminal app**, so the cluster's host key gets saved:
   ```bash
   ssh -i ~/.ssh/<key> <user>@login.explorer.northeastern.edu
   ```
   Type `yes` at the host-key prompt. Note whether it asks for a password or Duo, then type `exit`.

4. **Tell Claude Code** two things: the key file name, and whether step 3 asked for a password or Duo.

### What Claude Code does next

It tests a login that cannot prompt:

```bash
ssh -i ~/.ssh/<key> -o BatchMode=yes <user>@login.explorer.northeastern.edu hostname
```

| Result | What happens |
|---|---|
| Prints a hostname such as `explorer-02` | **Connected.** Claude Code runs cluster commands itself from here on. |
| Fails because Duo or a password is needed on every login | Use the **shared connection** below. |
| You'd rather not give access | Run the commands yourself and paste the output into the chat. |

If Claude Code asks permission to run an `ssh` command, approve it. You can also add an allow rule for `ssh -i ~/.ssh/<key>` in your Claude Code settings.

### Fallback: shared connection, only if Duo prompts on every login

You add this yourself. Claude Code isn't permitted to edit `~/.ssh/config`.

```
Host explorer
  HostName login.explorer.northeastern.edu
  User <user>
  IdentityFile ~/.ssh/<key>
  ControlMaster auto
  ControlPath ~/.ssh/cm-%C
  ControlPersist 8h
  ServerAliveInterval 60
```

Then run `ssh explorer` once in your own Terminal and complete Duo. For the next 8 hours, Claude Code's `ssh explorer '<command>'` calls reuse that login. Close it early with `ssh -O exit explorer`.

### Safety

- The private key never leaves your Mac. RC asks that you never copy it to shared or lab machines.
- To revoke access, regenerate the key in Open OnDemand.
- Everything Claude Code runs on the cluster shows up in your shell history there.

### First checks Claude Code runs on Explorer

```bash
sinfo -o "%20P %8a %10l %50G" | grep -iE 'partition|gpu'                # GPU partitions, time limits, GPU types
sacctmgr -nP show assoc user=$USER format=account,partition,qos         # what you're allowed to use
srun -p gpu --gres=gpu:1 --mem=16G --time=00:10:00 --pty nvidia-smi     # the GPU you actually get
df -h ~ /scratch/$USER                                                  # space for model weights
srun -p short --time=00:05:00 curl -sI https://pypi.org | head -1      # can compute nodes reach the internet?
```

**If every `srun` fails, even on `short`, with "Invalid account or account/partition combination specified"**, your login works but you have no Slurm account. `sacctmgr show assoc where user=$USER` prints nothing in that case. The partitions themselves allow all accounts, so only RC can fix this: email rchelp@northeastern.edu and ask them to add a Slurm association for your user.

The GPU's memory decides the model size:

| GPU memory | Model size |
|---|---|
| 80 GB or more | 30–70B |
| 32–48 GB | 14–32B |
| 16 GB or less | Not worth it over a laptop |

---

## Tips for running models on Explorer

- **Never run model servers on login nodes.** Start vLLM inside a Slurm job and point the pipeline at `http://localhost:8000/v1` on the same node.
- **Keep model weights in `/scratch/<user>`**, not in your home folder.
- **Expect GPU jobs to hit time limits.** The cache makes it safe to split one package across several jobs.
- **Copy results back** with `rsync -av <user>@login.explorer.northeastern.edu:<path>/runs/ runs/`.
- **If compute nodes have no outbound internet** (the last command under "First checks" tells you), run anything that calls Azure from your Mac and copy the cached results to Explorer.
- **Prefer models with no license gate**, such as most Qwen releases. Llama models need a Hugging Face token and an accepted license.

## Sources

- [SSH instructions for Explorer (RC, October 2026)](https://rc.northeastern.edu/2026/10/23/ssh-instructions-for-explorer/)
- [All About Explorer and the New H200 GPUs (RC)](https://rc.northeastern.edu/?p=7231)
- [Working with GPUs (RC docs)](https://rc-docs.northeastern.edu/en/explorer-main/gpus/index.html)
