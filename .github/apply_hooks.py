import re, sys

def rd(p):
    with open(p) as f:
        return f.read()

def wr(p, s):
    with open(p, "w") as f:
        f.write(s)

def fail(msg):
    print("HOOK PATCH FAILED: " + msg)
    sys.exit(1)

def balance(s):
    return (len(re.findall(r'^[ \t]*#[ \t]*if', s, re.M))
            - len(re.findall(r'^[ \t]*#[ \t]*endif', s, re.M)))

OLD = re.compile(
    r'^[ \t]*#[ \t]*(?:ifdef[ \t]+CONFIG_KSU\b|if[ \t]+defined\(CONFIG_KSU\))[^\n]*\n'
    r'.*?^[ \t]*#[ \t]*endif[^\n]*\n', re.S | re.M)

FILES = ["drivers/input/input.c", "fs/read_write.c", "fs/exec.c", "fs/open.c",
         "fs/stat.c", "kernel/reboot.c", "kernel/sys.c"]

for p in FILES:
    try:
        s = rd(p)
    except FileNotFoundError:
        print("skip (missing): " + p)
        continue
    b0 = balance(s)
    s2, n = OLD.subn("", s)
    if balance(s2) != b0:
        fail("unbalanced #if/#endif after cleaning " + p + " - clean it by hand")
    wr(p, s2)
    print("cleaned %s: removed %d old block(s)" % (p, n))
    left = [l.strip() for l in s2.split("\n") if "ksu_" in l or "CONFIG_KSU" in l]
    if left:
        fail("old KSU lines still in " + p + ": " + " | ".join(left))

def add_decl(s, limit, decl):
    if decl is None or decl in s:
        return s
    ms = [m for m in re.finditer(r'^#include[^\n]*\n', s, re.M) if m.start() < limit]
    if not ms:
        fail("no #include found for declarations")
    pos = ms[-1].end()
    return s[:pos] + decl + s[pos:]

def patch(path, func, anchor, code, decl=None, after=False):
    s = rd(path)
    if s.count(func) != 1:
        fail("%s: function not found exactly once: %s" % (path, func))
    i = s.index(func)
    j = s.find(anchor, i)
    if j < 0:
        fail("%s: anchor not found after %s: %r" % (path, func, anchor))
    if after:
        j += len(anchor)
    s = s[:j] + code + s[j:]
    s = add_decl(s, i, decl)
    wr(path, s)
    print("patched %s" % path)

H = "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
E = "#endif\n"

patch("fs/exec.c",
      "static int do_execveat_common(int fd, struct filename *filename,",
      "\tif (IS_ERR(filename))\n\t\treturn PTR_ERR(filename);\n",
      H + "\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);\n" + E + "\n",
      H + "extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n"
          "\t\t\t\tvoid *argv, void *envp, int *flags);\n"
          "extern int ksu_handle_post_execveat(int *fd, struct filename **filename_ptr,\n"
          "\t\t\t\tvoid *argv, void *envp, int *flags, int *retval);\n" + E)
patch("fs/exec.c",
      "static int do_execveat_common(int fd, struct filename *filename,",
      "out_ret:\n",
      H + "\tksu_handle_post_execveat(&fd, &filename, &argv, &envp, &flags, &retval);\n" + E,
      after=True)

patch("fs/open.c",
      "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)",
      "\tif (mode & ~S_IRWXO)",
      H + "\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n" + E + "\n",
      H + "extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n"
          "\t\t\t\tint *mode, int *flags);\n" + E)

patch("fs/stat.c",
      "SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,",
      "\terror = vfs_fstatat(dfd, filename, &stat, flag);",
      H + "\tksu_handle_stat(&dfd, &filename, &flag);\n" + E,
      H + "extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);\n"
          "extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);\n" + E)
patch("fs/stat.c",
      "SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)",
      "\treturn error;",
      H + "\tksu_handle_newfstat_ret(&fd, &statbuf);\n" + E + "\n")

patch("kernel/reboot.c",
      "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,",
      "\t/* We only trust the superuser with rebooting the system. */",
      H + "\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n" + E + "\n",
      H + "extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg);\n" + E)

print("ALL MANUAL HOOKS APPLIED")
  
