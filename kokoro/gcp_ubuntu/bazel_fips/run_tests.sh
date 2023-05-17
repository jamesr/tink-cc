#!/bin/bash
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

set -euo pipefail

# By default when run locally this script runs the command below directly on the
# host. The CONTAINER_IMAGE variable can be set to run on a custom container
# image for local testing. E.g.:
#
# CONTAINER_IMAGE="us-docker.pkg.dev/tink-test-infrastructure/tink-ci-images/linux-tink-cc-cmake:latest" \
#  sh ./kokoro/gcp_ubuntu/bazel_fips/run_tests.sh
#
RUN_COMMAND_ARGS=()
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_cc"
  readonly C_PREFIX="us-docker.pkg.dev/tink-test-infrastructure/tink-ci-images"
  readonly C_NAME="linux-tink-cc-cmake"
  readonly C_HASH="379a51d8aa072d27317a8fb8bdf84e2675f0c5c2a2ead5ae2ea0e514c9c4ea6f"
  CONTAINER_IMAGE="${C_PREFIX}/${C_NAME}@sha256:${C_HASH}"
  RUN_COMMAND_ARGS+=( -k "${TINK_GCR_SERVICE_KEY}" )
fi
readonly CONTAINER_IMAGE

if [[ -n "${CONTAINER_IMAGE}" ]]; then
  RUN_COMMAND_ARGS+=( -c "${CONTAINER_IMAGE}" )
fi

# Run build and tests with the BoringSSL FIPS module
# Prepare the workspace to use BoringCrypto which is in
# third_party/boringssl_fips; insert the local_repository instruction below
# in WORKSPACE.
APPEND_AFTER='workspace(name = "tink_cc")'
NUM_MATCHES="$(grep -c "${APPEND_AFTER}" WORKSPACE)"
if (( $? != 0 || NUM_MATCHES != 1)); then
  echo "ERROR: Could not patch WORKSPACE to build BoringSSL with FIPS module"
  exit 1
fi
mapfile LOCAL_FIPS_REPOSITORY <<EOM
local_repository(
  name = "boringssl",
  path = "third_party/boringssl_fips",
)
EOM
printf -v INSERT_TEXT '\\n%s' "${LOCAL_FIPS_REPOSITORY[@]//$'\n'/}"
sed -i.bak "/${APPEND_AFTER}/a \\${INSERT_TEXT}" WORKSPACE

BAZEL_FLAGS=(
  --//tink/config:use_only_fips=True
  --build_tag_filters=fips,-requires_boringcrypto_update
)

./kokoro/testutils/run_command.sh "${RUN_COMMAND_ARGS[@]}" \
    bazelisk build "${BAZEL_FLAGS[@]}" -- ... \
    "&&" bazelisk test "${BAZEL_FLAGS[@]}" \
      --build_tests_only \
      --test_output=errors \
      --test_tag_filters=fips,-requires_boringcrypto_update -- ...

mv WORKSPACE.bak WORKSPACE
