import os, pytest, time
import subprocess
from multiprocessing import context  # type: ignore

# XXX


def exitcode(process: context.ForkProcess):
    if isinstance(process, subprocess.Popen):
        return process.poll()
    else:
        if process.is_alive():
            return None
        else:
            return process.exitcode


def wait_for_mount(mount_process: context.ForkProcess, mnt_dir: str):
    print(f"wait_for_mount({mnt_dir})")
    elapsed = 0
    while elapsed < 30:
        if os.path.ismount(mnt_dir):
            return True
        if exitcode(mount_process) is not None:
            pytest.fail("file system process terminated prematurely")
        time.sleep(0.1)
        elapsed += 0.1
    pytest.fail("mountpoint failed to come up")


def cleanup(mount_process: context.ForkProcess, mnt_dir: str):
    print(f"cleanup({mnt_dir})")

    subprocess.call(
        ["fusermount", "-z", "-u", mnt_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    mount_process.terminate()
    if isinstance(mount_process, subprocess.Popen):
        try:
            mount_process.wait(1)
        except subprocess.TimeoutExpired:
            mount_process.kill()
    else:
        mount_process.join(5)
        if mount_process.exitcode is None:
            mount_process.kill()


def umount(mount_process: context.ForkProcess, mnt_dir: str):
    subprocess.check_call(["fusermount", "-z", "-u", mnt_dir])
    assert not os.path.ismount(mnt_dir)

    if isinstance(mount_process, subprocess.Popen):
        try:
            code = mount_process.wait(5)
            if code == 0:
                return
            pytest.fail("file system process terminated with code %s" % (code,))
        except subprocess.TimeoutExpired:
            mount_process.terminate()
            try:
                mount_process.wait(1)
            except subprocess.TimeoutExpired:
                mount_process.kill()
    else:
        mount_process.join(5)
        code = mount_process.exitcode
        if code == 0:
            return
        elif code is None:
            mount_process.terminate()
            mount_process.join(1)
        else:
            pytest.fail("file system process terminated with code %s" % (code,))

    pytest.fail("mount process did not terminate")
