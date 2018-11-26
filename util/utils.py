# -*- coding: utf-8 -*-
"""
A collection of utility functions to generate Dockerfiles automagically.
"""
import errno
import glob
import os
import stat
from subprocess import check_call

import util.parser

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_DOCKERFILE_TEMPLATE = "Dockerfile.template"
DEFAULT_DOCKERFILE_USER = "tslno"
DELIMITER = "-"

# Denotes an empty file in the root directory, so e.g. get_tag
# function knows when it has reached its base case.
ROOT = ".root"


def create(args, parser_func=util.parser.parse):
    """
    Creates Dockerfiles for all found config files.
    :param args: regex paths to config files.
    :param parser_func: the function used for parsing the config files.
    :return: None.
    """
    configs = []
    for arg in args:
        if os.path.isfile(arg):
            configs.append(arg)
        else:
            configs.extend(glob.glob(arg))
    if not configs:
        configs = glob.glob("**/**/config")
    for config in configs:
        print "creating Dockerfile(s) from '{}'".format(config)
        for conf in parser_func(config):
            create_dockerfile(config, conf)


def get_tag(directory, path=None, delimiter=DELIMITER):
    """
    Creates tags for Docker images based on the directory structure.
    If get_tag is invoked within e.g. 'node/gcloud' directory, then
    the tag created will be 'node-gcloud'.
    :param directory: a directory where the Docker template resides.
    :param path: current tag path.
    :param delimiter: the string character between directory names, e.g. '-'.
    :return: a string denoting the Docker tag.
    """
    if not os.path.isdir(directory):
        raise Exception("'{}' is not a directory".format(directory))
    if path is None:
        path = []
    if ROOT in os.listdir(directory):
        return delimiter.join(path)
    path.insert(0, os.path.basename(directory))
    parent = os.path.abspath(os.path.join(directory, os.pardir))
    return get_tag(parent, path, delimiter)


def render(template, args):
    """
    Takes a template file and replaces its name arguments with the provided
    values.
    :param template: the template file.
    :param args: a dict of name args to be applied to the template file.
    :return: a string denoting a rendered template.
    """
    if not os.path.isfile(template):
        raise Exception("cannot find the template: '{}'".format(template))
    with open(template, 'r') as tmp:
        content = tmp.read()
    return content.format(**args)


def render_build(args):
    """
    Renders the build script template.
    :param args: a dict of name args to be applied to the template file.
    :return: a string denoting a rendered build template.
    """
    template = os.path.join(CURRENT_DIR, 'templates', 'build.template')
    return render(template, args)


def render_deploy(args):
    """
    Renders the deploy script template.
    :param args: a dict of name args to be applied to the template file.
    :return: a string denoting a rendered deploy template.
    """
    template = os.path.join(CURRENT_DIR, 'templates', 'deploy.template')
    return render(template, args)


def find_all_scripts(script_name, directory):
    """
    Finds all scripts that match script_name in all subdirectories.
    :param script_name: the script name
    :param directory: the parent directory
    :return: a list of scripts with fully qualified paths.
    """
    scripts = []
    for dirpath, _, filenames in os.walk(directory):
        files = [os.path.join(dirpath, f)
                 for f in filenames
                 if f == script_name and dirpath is not directory]
        scripts.extend(files)
    return scripts


def exec_all_scripts(script_name, directory):
    """
    Executes all scripts that match script_name in all subdirectories.
    :param script_name: the script name
    :param directory: the parent directory
    :return: None.
    """
    scripts = find_all_scripts(script_name, directory)
    for script in scripts:
        check_call(script)


def create_dockerfile(root_file, args):
    """
    Creates a Dockerfile from a template.
    :param root_file: the file where this function is called from.
    :param args: the args to render the Docker template.
    :return: None.
    """
    directory = os.path.dirname(os.path.realpath(root_file))
    if not os.path.isdir(directory):
        raise Exception("'{}' is not a directory".format(directory))

    version = args["version"]
    if version in args:
        version = args["version"] = args[version]
    if not version:
        raise Exception("no version found in args: {}".format(args))

    dockerfile_dir = create_dir(directory, "images", version)
    args["dockerfile_directory"] = dockerfile_dir

    template_name = args.get("template", DEFAULT_DOCKERFILE_TEMPLATE)
    template = os.path.join(directory, template_name)
    if not os.path.isfile(template):
        raise Exception("cannot find the template: '{}'".format(template))

    dockerfile_content = render(template, args)
    dockerfile = _create_file(dockerfile_dir, "Dockerfile", dockerfile_content)
    args["dockerfile"] = dockerfile

    if "tag" not in args:
        args["tag"] = get_tag(directory)

    if "user" not in args:
        args["user"] = DEFAULT_DOCKERFILE_USER

    build_content = render_build(args)
    buildscript = _create_script(dockerfile_dir, 'build', build_content)
    args["buildscript"] = buildscript

    deploy_content = render_deploy(args)
    _create_script(dockerfile_dir, 'deploy', deploy_content)


def create_dir(parent, *paths):
    """
    Creates a directory at a given path.
    :param parent: the parent directory
    :param paths: additional subdirectories.
    :return: the path of the created directory.
    """
    dir_path = os.path.join(parent, *paths)
    try:
        os.makedirs(dir_path)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise
    return dir_path


def _create_file(parent, name, content):
    """
    Creates a file at a given path and adds the content.
    :param parent: the parent directory.
    :param name: the file name.
    :param content: the file content.
    :return: the path of the created file.
    """
    file_path = os.path.join(parent, name)
    with open(file_path, 'w+') as buf:
        buf.write(content)
    return file_path


def make_executable(file_path):
    """ Sets execute permissions on a given file. """
    if not os.path.isfile(file_path):
        raise Exception("'{}' is not a file".format(file_path))
    fstat = os.stat(file_path)
    os.chmod(file_path, fstat.st_mode | stat.S_IEXEC)


def _create_script(parent, name, content):
    """
    Creates a bash script at a given path and adds the content.
    :param parent: the parent directory.
    :param name: the script name.
    :param content: the script content.
    :return: the path of the created script.
    """
    script = _create_file(parent, name, content)
    make_executable(script)
    return script
