#!/usr/bin/env python3

# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################
r"""Utility that replaces http_archive with local_repository in WORKSPACE files.

Usage:
  ./kokoro/testutils/replace_http_archive_with_local_repository.py \
    -f <workspace directory> \
    -t <root folder containing the local dependencies>

For examples:
  # Assume we have:
  #   /tmp/git/tink_cc
  #   /tmp/git/tink_examples
  # From /tmp/git/tink_examples run:
  ./kokoro/testutils/replace_http_archive_with_local_repository.py \
    -f "cc/WORKSPACE" \
    -t /tmp/git
"""

import argparse
import os
import re
import textwrap

# Holds (bazel dependency name, git repo name, git branch).
_TINK_REPO_NAME_AND_BRANCH = (
    ('tink_cc', 'tink-cc', 'master'),
    ('tink_cc_awskms', 'tink-cc-awskms', 'main'),
    ('tink_cc_gcpkms', 'tink-cc-gcpkms', 'main'),
    ('tink_java', 'tink-java', 'main'),
    ('tink_java_awskms', 'tink-java-awskms', 'main'),
    ('tink_java_gcpkms', 'tink-java-gcpkms', 'main'),
    ('tink_py', 'tink-py', 'main'),
    ('tink_go', 'tink-go', 'main'),
    ('tink_go_gcpkms', 'tink-go-gcpkms', 'main'),
    ('com_github_tink_crypto_tink_go', 'tink-go', 'main'),
    ('com_github_tink_crypto_tink_go_gcpkms', 'tink-go-gcpkms', 'main'),
)


def _replace_http_archive_with_local_repository(workspace_content: str,
                                                bazel_dep_name: str,
                                                git_repo_name: str,
                                                local_dir_path: str,
                                                branch: str) -> str:
  """Replaces a single http_archive with local_repository in workspace_content.

  Args:
    workspace_content: Content of the WORKSPACE file to modify.
    bazel_dep_name: Name of the bazel dependency, e.g., tink_cc.
    git_repo_name: Name of the repo in github.com/tink-crypto, e.g., tink-cc.
    local_dir_path: Path to the local folder, e.g., /tmp/git/tink_cc.
    branch: Main branch used by the repo, e.g, main.

  Returns:
    The modified WORKSPACE file content.
  """
  before = textwrap.dedent(f"""\
      http_archive(
          name = "{bazel_dep_name}",
          urls = ["https://github.com/tink-crypto/{git_repo_name}/archive/{branch}.zip"],
          strip_prefix = "{git_repo_name}-{branch}",
      )""")
  after = textwrap.dedent(f"""\
      local_repository(
          name = "{bazel_dep_name}",
          path = "{local_dir_path}",
      )""")
  return workspace_content.replace(before, after)


def _replace_all_http_archive_with_local_repository(
    workspace_content: str, local_deps_root_dir: str) -> str:
  """Replaces all http_archive with local_repository in workspace_content.

  Args:
    workspace_content: Content of the WORKSPACE file to modify.
    local_deps_root_dir: Directory that contains the local dependencies to use.

  Returns:
    The modified WORKSPACE file content.
  """
  for bazel_dep_name, git_repo_name, branch in _TINK_REPO_NAME_AND_BRANCH:
    workspace_content = _replace_http_archive_with_local_repository(
        workspace_content=workspace_content,
        bazel_dep_name=bazel_dep_name,
        git_repo_name=git_repo_name,
        local_dir_path=os.path.join(local_deps_root_dir,
                                    git_repo_name.replace('-', '_')),
        branch=branch)
  # Remove loading of http_archive if there are no other http_archive entries
  # left in workspace_content.
  if not re.search(
      r'^[^#]*http_archive\(', workspace_content, flags=re.MULTILINE):
    http_archive_load = textwrap.dedent("""
        load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
        """)
    workspace_content = workspace_content.replace(http_archive_load, '')
  return workspace_content


def main():
  parser = argparse.ArgumentParser(
      description='Replaces http_archive rules with local_repository rules')
  parser.add_argument('--workspace_file_path', '-f', required=True)
  parser.add_argument('--local_deps_root_dir', '-t', required=True)
  args = parser.parse_args()

  with open(args.workspace_file_path, 'r') as workspace_file:
    content = workspace_file.read()
    content = _replace_all_http_archive_with_local_repository(
        content, args.local_deps_root_dir)
  with open(args.workspace_file_path, 'w') as workspace_file:
    workspace_file.write(content)


if __name__ == '__main__':
  main()