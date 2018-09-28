#!/usr/bin/env python3
"""Documentation needed
"""

import argparse
import os
import sys
import shutil
import subprocess
import shlex
import stat
import json


VERBOSE = False

def getRepo(targetRepo, baseurl):
    repo_template = """[%s]
name=%s
baseurl=%s
enabled=1"""
    return repo_template % (targetRepo, targetRepo, baseurl)


class SdkManager():
    def __init__(self, inputFiles, outputDir):
        self._outputDir = os.path.abspath(outputDir)

        self._initConf = {}
        self.__SDK_BOOTSTRAP = None
        self.__initInPutJson(inputFiles)

        self.__checkSdkBootStrap()

        self.__createRootfsEnv()
        self.__createRootfsTargetRepo()
        self.__createRootfsNativeRepo()
        self.__createTargetDnfTools()
        self.__createNativeDnfTools()
        self.__createInitEnv()

    def __checkSdkBootStrap(self):
        if 'SDK_BOOTSTRAP' in os.environ:
            self.__SDK_BOOTSTRAP = os.environ['SDK_BOOTSTRAP']
        else:
            print("ERROR: SDK_BOOTSTRAP is not define in the environement.")
            print("ERROR: please source SDK bootstrap environement before init your SDK.")
            exit(1)

    def __initInPutJson(self, inputFiles):
        for jsonFile in inputFiles:
            with open(jsonFile, "r") as infile:
                self._initConf.update(json.load(infile))

    def __createPath(self, aPath):
        if not os.path.exists(aPath):
            os.makedirs(aPath)

    def __getSdkConf(self, var):
        return self._initConf["sdk_conf"][var]

    def __getRuntimeConf(self, var):
        return self._initConf["runtime_conf"][var]

    def __cleanOldRepo(self, SDK_PATH):
        if VERBOSE:
            print("WARNING: Going to remove %s" % (SDK_PATH))
        if SDK_PATH != "/":
            cmd_clean = "sudo rm -fr %s" % (SDK_PATH)
            args = shlex.split(cmd_clean)
            subprocess.check_output(args)

    def __getRepoRuntimeName(self):
        return self._initConf["repo"]["runtime"]["Name"]

    def __createRootfsEnv(self):
        self.__SDK_PATH = os.path.join(
            self._outputDir, self.__getRepoRuntimeName() + "-sdk")
        self.__cleanOldRepo(self.__SDK_PATH)
        self.__createPath(self.__SDK_PATH)

        self.__SDKSYSROOT = self.__SDK_PATH + "/sysroots"
        self.__SDKSYSROOT_LOG = self.__SDK_PATH + "/log"

        self.__DISTRO_CODENAME = self.__getSdkConf("DISTRO_CODENAME")
        self.__MACHINE_ARCH = self.__getSdkConf("MACHINE_ARCH")
        self.__SDK_OS = self.__getSdkConf("SDK_OS")
        self.__SDK_VENDOR = self.__getSdkConf("SDK_VENDOR")
        self.__SDK_ARCH = self.__getSdkConf("SDK_ARCH")
        self.__TARGET_OS = self.__SDK_OS
        self.__TUNE_PKGARCH = self.__getSdkConf("TUNE_PKGARCH")
        self.__TARGET_VENDOR = self.__getRuntimeConf("TARGET_VENDOR")
        self.__TARGET_SYS = self.__getRuntimeConf("TARGET_SYS")
        self.__SDK_VERSION = self.__getSdkConf("SDK_VERSION")
        self.__DISTRO = self.__getSdkConf("DISTRO")
        self.__HOST_SYS = self.__getSdkConf("HOST_SYS")
        self.__REAL_MULTIMACH_TARGET_SYS = self.__TUNE_PKGARCH + \
            self.__TARGET_VENDOR + "-" + self.__TARGET_OS
        self.__SDKTARGETSYSROOT = self.__SDKSYSROOT + "/" + self.__REAL_MULTIMACH_TARGET_SYS
        self.__SDK_SYS = self.__SDK_ARCH + self.__SDK_VENDOR + "-" + self.__SDK_OS
        self.__SDKPATHNATIVE = self.__SDKSYSROOT + "/" + self.__SDK_SYS

        self.__NATIVE_SYSROOT_SETUP = self.__getSdkConf("SDKPATH")
        self.__SDK_NATIVE_SUBSYSROOT = self.__NATIVE_SYSROOT_SETUP + "/sysroots/" + self.__SDK_SYS

        self.__SDKPATHNATIVE_DNF_LOG = self.__SDKSYSROOT_LOG + "/" + self.__SDK_SYS + "/log"
        self.__SDKTARGETSYSROOT_DNF_LOG = self.__SDKSYSROOT_LOG + \
            "/" + self.__REAL_MULTIMACH_TARGET_SYS + "/log"

        self.__createPath(self.__SDKTARGETSYSROOT)
        self.__createPath(self.__SDKPATHNATIVE)
        self.__NATIVE_SUBSYSROOT_DIR = self.__SDKPATHNATIVE + self.__NATIVE_SYSROOT_SETUP + "/sysroots"
        self.__createPath(self.__NATIVE_SUBSYSROOT_DIR)
        self.__createPath(os.path.dirname(self.__SDKPATHNATIVE + self.__NATIVE_SYSROOT_SETUP))
        os.symlink(os.path.relpath(self.__SDKPATHNATIVE, self.__NATIVE_SUBSYSROOT_DIR), self.__SDKPATHNATIVE + self.__SDK_NATIVE_SUBSYSROOT)

        self.__createPath(self.__SDKTARGETSYSROOT_DNF_LOG)
        self.__createPath(self.__SDKPATHNATIVE_DNF_LOG)

        for SYSROOT in [self.__SDKPATHNATIVE, self.__SDKTARGETSYSROOT]:
            self.__createPath(SYSROOT + "/etc/dnf/vars")
            self.__createPath(SYSROOT + "/etc/rpm")
            self.__createPath(SYSROOT + "/etc/yum.repos.d/")
            self.__createPath(SYSROOT + "/usr/lib/rpm")

            with open(SYSROOT + "/etc/dnf/dnf.conf", "w") as f:
                f.write("")
            with open(SYSROOT + "/usr/lib/rpm/rpmrc", "w") as f:
                f.write("")

            with open(SYSROOT + "/etc/dnf/vars/releasever", "w") as f:
                f.write(self.__DISTRO_CODENAME + "\n")
            with open(SYSROOT + "/etc/rpm/macros", "w") as f:
                f.write("%_transaction_color 7\n")
                f.write("%_prefer_color 7\n")
            with open(SYSROOT + "/usr/lib/rpm/macros", "w") as f:
                f.write("%_var /var\n")
                f.write("%_dbpath %{_var}/lib/rpm\n")
                f.write("%_rpmlock_path %{_dbpath}/.rpm.lock\n")

        for script in ['toolchain-shar-relocate.sh', 'relocate_sdk.py']:
            path = shutil.which(script)
            cmd_cp = "cp %s %s/" % (path, self.__SDK_PATH)
            args = shlex.split(cmd_cp)
            subprocess.check_output(args)

    def getRunTimeRepo(self):
        repoDico = {}
        for repo in self._initConf["repo"]["runtime"]:
            if repo != "Name":
                repoDico[repo] = self._initConf["repo"]["runtime"][repo]
        return repoDico

    def getSdkRepo(self):
        repoDico = {}
        for repo in self._initConf["repo"]["sdk"]:
            if repo != "Name":
                repoDico[repo] = self._initConf["repo"]["sdk"][repo]
        return repoDico

    def __createRootfsTargetRepo(self):
        archs = self.__getRuntimeConf(
            "ALL_MULTILIB_PACKAGE_ARCHS").replace("-", "_")
        listArchs = [i for i in reversed(archs.split()) if i not in [
            "any", "all", "noarch"]]
        with open(self.__SDKTARGETSYSROOT + "/etc/dnf/vars/arch", "w") as f:
            f.write(":".join(listArchs) + "\n")
        with open(self.__SDKTARGETSYSROOT + "/etc/rpmrc", "w") as f:
            f.write("arch_compat: %s: %s\n" % (self.__MACHINE_ARCH,
                                               archs if len(archs) > 0 else self.__MACHINE_ARCH))

        with open(self.__SDKTARGETSYSROOT + "/etc/rpm/platform", "w") as f:
            f.write(self.__MACHINE_ARCH + "-pc-linux\n")

        runtimeRepo = self.getRunTimeRepo()
        for targetRepo in runtimeRepo:
            with open(self.__SDKTARGETSYSROOT + "/etc/yum.repos.d/" + targetRepo + ".repo", "w") as f:
                f.write(getRepo(targetRepo, runtimeRepo[targetRepo]))

    def __createRootfsNativeRepo(self):
        repo_cpu = self.__SDK_ARCH + "_nativesdk"
        with open(self.__SDKPATHNATIVE + "/etc/dnf/vars/arch", "w") as f:
            f.write(repo_cpu + ":bogusarch\n")
        with open(self.__SDKPATHNATIVE + "/etc/rpmrc", "w") as f:
            f.write("arch_compat: " + repo_cpu + ": all any noarch " + repo_cpu + "\n")
        with open(self.__SDKPATHNATIVE + "/etc/rpm/platform", "w") as f:
            f.write(repo_cpu + "-pc-linux\n")

        runtimeRepo = self.getSdkRepo()
        for hostRepo in runtimeRepo:
            if hostRepo != "":
                with open(self.__SDKPATHNATIVE + "/etc/yum.repos.d/" + hostRepo + ".repo", "w") as f:
                    f.write(getRepo(hostRepo, runtimeRepo[hostRepo]))

    def __createTargetDnfTools(self):
        script_path = self.__SDK_PATH + "/dnf4Target"
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("export SDK_BOOTSTRAP=\"" + self.__SDK_BOOTSTRAP + "\"\n")
            f.write("export SDKTARGETSYSROOT=\"" + self.__SDKTARGETSYSROOT + "\"\n")
            f.write(
                "source ${SDK_BOOTSTRAP}/environment-setup-" + self.__SDK_SYS + "\n")
            f.write("export RPM_ETCCONFIGDIR=${SDKTARGETSYSROOT}\n")
            f.write("export RPM_CONFIGDIR=${SDKTARGETSYSROOT}/usr/lib/rpm\n")
            f.write("export D=${SDKTARGETSYSROOT}\n")
            f.write("export SUDO_EXEC=\"$(which \"sudo\") \"PATH=$PATH\" -E\"\n")
            f.write("export DNF=$(which \"dnf\")\n")
            DNF_TARGET_CMD = "$SUDO_EXEC ${DNF}  -y -c %s/etc/dnf/dnf.conf --setopt=reposdir=%s/etc/yum.repos.d --installroot=%s --setopt=logdir=%s --nogpgcheck" % (
                self.__SDKTARGETSYSROOT, self.__SDKTARGETSYSROOT, self.__SDKTARGETSYSROOT, self.__SDKTARGETSYSROOT_DNF_LOG)
            f.write("export DNF_TARGET_CMD=\"" + DNF_TARGET_CMD + "\"\n")
            f.write("${DNF_TARGET_CMD} $@\n")

        os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP |
                 stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)

    def __createNativeDnfTools(self):
        script_path = self.__SDK_PATH + "/dnf4Native"
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("export SDK_BOOTSTRAP=\"" + self.__SDK_BOOTSTRAP + "\"\n")
            f.write("export SDKPATHNATIVE=\"" + self.__SDKPATHNATIVE + "\"\n")
            f.write("export SDKTARGETSYSROOT=\"" + self.__SDKTARGETSYSROOT + "\"\n")
            f.write(
                "source ${SDK_BOOTSTRAP}/environment-setup-" + self.__SDK_SYS + "\n")
            f.write("export RPM_ETCCONFIGDIR=${SDKPATHNATIVE}\n")
            f.write("export RPM_CONFIGDIR=${SDKPATHNATIVE}/usr/lib/rpm\n")
            f.write("export D=${SDKPATHNATIVE}\n")
            f.write("export SUDO_EXEC=\"$(which \"sudo\") \"PATH=$PATH\" -E\"\n")
            f.write("export DNF=$(which \"dnf\")\n")
            DNF_HOST_CMD = "$SUDO_EXEC ${DNF}   -y -c %s/etc/dnf/dnf.conf --setopt=reposdir=%s/etc/yum.repos.d --installroot=%s --setopt=logdir=%s --nogpgcheck" % (
                self.__SDKPATHNATIVE, self.__SDKPATHNATIVE, self.__SDKPATHNATIVE, self.__SDKPATHNATIVE_DNF_LOG)
            f.write("export DNF_HOST_CMD=\"" + DNF_HOST_CMD + "\"\n")
            f.write("${DNF_HOST_CMD} $@\n")
            f.write("if [ $1 == \"makecache\" ]; then exit 0 ;fi\n")
            f.write("export env_setup_script=" + self.__SDK_PATH + "/env-init-SDK.sh\n")
            f.write("export target_sdk_dir=$SDKPATHNATIVE\n")
            f.write("export relocate=1\n")
            f.write("export DEFAULT_INSTALL_DIR=" + self.__SDK_NATIVE_SUBSYSROOT + "\n")
            f.write("bash " + self.__SDK_PATH + "/toolchain-shar-relocate.sh\n")
            f.write("export native_sysroot=${SDKPATHNATIVE}\n")
            postInstallFix = '''
for replace in ${SDKPATHNATIVE}; do
        $SUDO_EXEC find $replace -type f
done | xargs -n100 file | grep ":.*\(ASCII\|script\|source\).*text" | \\
    awk -F':' '{printf "\\"%s\\"\\n", $1}' | \\
    grep -Ev "$target_sdk_dir/(environment-setup-*|relocate_sdk*|${0##*/})" | \\
    xargs -n100 $SUDO_EXEC sed -i \\
        -e "s:#SDKTARGETSYSROOT#:${SDKTARGETSYSROOT}:g"
'''
            f.write(postInstallFix)

        os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP |
                 stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)

    def __createInitEnv(self):
        with open(os.path.join(self.__SDK_PATH, "env-init-SDK.sh"), "w") as f:
            f.write("export SDKTARGETSYSROOT=\"%s\"\n" %
                    self.__SDKTARGETSYSROOT)
            BINDIR = self.__SDKPATHNATIVE + "/usr/bin"
            SBINDIR = self.__SDKPATHNATIVE + "/usr/sbin"
            BASEBIN = self.__SDKPATHNATIVE + "/bin"
            BASESBIN = self.__SDKPATHNATIVE + "/sbin"
            # It seems to be the same as BASEBIN
            BASESBIN_HOST = BINDIR + "/../" + self.__HOST_SYS + "/bin"
            BINDIR_CROSS = BINDIR + "/" + self.__TARGET_SYS
            EXTRAPATH = ""
            PATH = BINDIR + ":" + SBINDIR + ":" + BASEBIN + ":" + BASESBIN + \
                ":" + BASESBIN_HOST + ":" + BINDIR_CROSS + EXTRAPATH + ":$PATH"

            f.write("export PATH=\"%s\"\n" % PATH)
            f.write("export CONFIG_SITE=\"%s\"\n" % (self.__SDKPATHNATIVE +
                                                     self.__NATIVE_SYSROOT_SETUP + "/site-config-" + self.__REAL_MULTIMACH_TARGET_SYS))
            f.write("export OECORE_NATIVE_SYSROOT=\"%s\"\n" %
                    self.__SDKPATHNATIVE)
            f.write("export OECORE_ACLOCAL_OPTS=\"%s\"\n" %
                    ("-I " + self.__SDKPATHNATIVE + "/usr/share/aclocal"))
            f.write("unset LD_LIBRARY_PATH\n")
            NATIVE_SYSROOT_ENV = self.__SDKPATHNATIVE + self.__NATIVE_SYSROOT_SETUP + "/yomo-environment-setup-" + self.__REAL_MULTIMACH_TARGET_SYS
            f.write("source %s\n" % NATIVE_SYSROOT_ENV)


def concatenateJson(inputJson, outputJson):
    output_Json = {}

    for jsonFile in inputJson:
        with open(jsonFile, "r") as infile:
            aDico = json.load(infile)
            output_Json.update(aDico)

    with open(outputJson, "w") as outfile:
        json.dump(output_Json, outfile, sort_keys=True, indent=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-i", "--inputJson", action='append',
                        help="SDK JSON conf files (Can have multiple)")
    parser.add_argument("-o", "--output", help="rootfs sdk directory")
    parser.add_argument("-j", "--outputJson", help="Save output Json file.")

    args = parser.parse_args()

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        exit(1)

    if args.verbose:
        global VERBOSE
        VERBOSE = True
    if args.output is None and args.outputJson is None:
        print("No output option")
        exit(1)
    if args.inputJson is None:
        print("No input JSon file")
        exit(1)

    if args.outputJson:
        concatenateJson(args.inputJson, args.outputJson)

    SdkManager(args.inputJson, args.output)


if __name__ == '__main__':
    main()
