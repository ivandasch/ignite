# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Checks custom parametrizers.
"""

import itertools
from unittest.mock import Mock

import pytest
from ducktape.mark import parametrized, parametrize, matrix, ignore
from ducktape.mark.mark_expander import MarkedFunctionExpander

from ignitetest.utils._mark import IgniteVersionParametrize, ignite_versions, version_if
from ignitetest.utils.version import IgniteVersion, V_2_8_0, V_2_8_1, V_2_7_6, DEV_BRANCH


def expand_function(*, func, sess_ctx):
    """
    Inject parameters into function and generate context list.
    """
    assert parametrized(func)
    assert next(filter(lambda x: isinstance(x, IgniteVersionParametrize), func.marks), None)

    return MarkedFunctionExpander(session_context=sess_ctx, function=func).expand()


def mock_session_ctx(*, global_args=None):
    """
    Create mock of session context.
    """
    sess_ctx = Mock()
    sess_ctx.globals = global_args if global_args else {}

    return sess_ctx


class CheckIgniteVersions:
    """
    Checks @ignite_version parametrization.
    """
    single_params = itertools.product(
        [[str(V_2_8_1)], [str(V_2_8_1), str(DEV_BRANCH)]],
        [{}, {'ignite_versions': 'dev'}, {'ignite_versions': ['2.8.1', 'dev']}]
    )

    @pytest.mark.parametrize(
        ['versions', 'global_args'],
        list(map(lambda x: pytest.param(x[0], x[1]), single_params))
    )
    def check_injection(self, versions, global_args):
        """
        Checks parametrization with single version.
        """
        @ignite_versions(*versions, version_prefix='ver')
        def function(ver):
            return IgniteVersion(ver)

        context_list = expand_function(func=function, sess_ctx=mock_session_ctx(global_args=global_args))

        self._check_injection(context_list, versions=versions, global_args=global_args)

    pair_params = itertools.product(
        [[(str(DEV_BRANCH), str(V_2_8_1))], [(str(DEV_BRANCH), str(V_2_8_0)), (str(DEV_BRANCH), str(V_2_8_1))]],
        [{}, {'ignite_versions': [['2.8.1', '2.7.6'], ['2.8.1', '2.8.0']]}, {'ignite_versions': [['dev', '2.8.1']]}]
    )

    @pytest.mark.parametrize(
        ['versions', 'global_args'],
        list(map(lambda x: pytest.param(x[0], x[1]), pair_params))
    )
    def check_injection_pairs(self, versions, global_args):
        """
        Checks parametrization with pair of versions.
        """
        @ignite_versions(*versions, version_prefix='pair')
        def function(pair_1, pair_2):
            return IgniteVersion(pair_1), IgniteVersion(pair_2)

        context_list = expand_function(func=function, sess_ctx=mock_session_ctx(global_args=global_args))

        self._check_injection(context_list, versions=versions, global_args=global_args, pairs=True)

    @pytest.mark.parametrize(
        ['versions', 'version_prefix', 'global_args'],
        [
            pytest.param([(DEV_BRANCH, V_2_8_1)], 'ver', {}),
            pytest.param([DEV_BRANCH], 'ver', {'ignite_versions': [['dev', '2.8.1']]}),
            pytest.param([DEV_BRANCH], 'invalid_prefix', {})
        ]
    )
    def check_injection_fail(self, versions, version_prefix, global_args):
        """
        Check incorrect injecting variables with single parameter.
        """
        @ignite_versions(*versions, version_prefix=version_prefix)
        def function(ver):
            return IgniteVersion(ver)

        with pytest.raises(Exception):
            context_list = expand_function(func=function, sess_ctx=mock_session_ctx(global_args=global_args))

            self._check_injection(context_list, versions=versions, global_args=global_args)

    @pytest.mark.parametrize(
        ['versions', 'version_prefix', 'global_args'],
        [
            pytest.param([DEV_BRANCH, V_2_8_1], 'pair', {}),
            pytest.param([(DEV_BRANCH, V_2_8_1)], 'pair', {'ignite_versions': 'dev'}),
            pytest.param([(DEV_BRANCH, V_2_8_1)], 'pair', {'ignite_versions': ['dev', '2.8.1']}),
            pytest.param([(DEV_BRANCH, V_2_8_1)], 'invalid_prefix', {})
        ]
    )
    def check_injection_pairs_fail(self, versions, version_prefix, global_args):
        """
        Check incorrect injecting with pairs of versions.
        """
        @ignite_versions(*versions, version_prefix=version_prefix)
        def function(pair_1, pair_2):
            return IgniteVersion(pair_1), IgniteVersion(pair_2)

        with pytest.raises(Exception):
            context_list = expand_function(func=function, sess_ctx=mock_session_ctx(global_args=global_args))

            self._check_injection(context_list, versions=versions, global_args=global_args, pairs=True)

    def check_with_others_marks(self):  # pylint: disable=R0201
        """
        Checks that ignite version parametrization works with others correctly.
        """
        @ignite_versions(str(DEV_BRANCH), str(V_2_8_1), version_prefix='ver')
        @parametrize(x=10, y=20)
        @parametrize(x=30, y=40)
        def function_parametrize(ver, x, y):
            return ver, x, y

        @ignite_versions((str(DEV_BRANCH), str(V_2_8_1)), (str(V_2_8_1), str(V_2_7_6)), version_prefix='pair')
        @matrix(i=[10, 20], j=[30, 40])
        def function_matrix(pair_1, pair_2, i, j):
            return pair_1, pair_2, i, j

        @ignore(ver=str(DEV_BRANCH))
        @ignite_versions(str(DEV_BRANCH), str(V_2_8_1), version_prefix='ver')
        def function_ignore(ver):
            return ver

        context_list = expand_function(func=function_parametrize, sess_ctx=mock_session_ctx())
        context_list += expand_function(func=function_matrix, sess_ctx=mock_session_ctx())
        context_list += expand_function(func=function_ignore, sess_ctx=mock_session_ctx())

        assert len(context_list) == 14
        assert len(list(filter(lambda x: x.function_name == function_parametrize.__name__, context_list))) == 4
        assert len(list(filter(lambda x: x.function_name == function_matrix.__name__, context_list))) == 8
        assert len(list(filter(lambda x: x.function_name == function_ignore.__name__, context_list))) == 2
        assert len(list(filter(lambda x: x.ignore, context_list))) == 1

    @staticmethod
    def _check_injection(context_list, *, versions, global_args=None, pairs=False):
        if global_args:
            global_versions = global_args['ignite_versions']

            if isinstance(global_versions, str):
                assert not pairs

                check_versions = [IgniteVersion(global_versions)]
            elif isinstance(global_args['ignite_versions'], tuple):
                assert pairs

                check_versions = [tuple(map(IgniteVersion, global_versions))]
            elif pairs:
                check_versions = list(map(lambda x: (IgniteVersion(x[0]), IgniteVersion(x[1])), global_versions))
            else:
                check_versions = list(map(IgniteVersion, global_versions))
        else:
            check_versions = list(map(IgniteVersion, versions)) if not pairs else \
                list(map(lambda x: (IgniteVersion(x[0]), IgniteVersion(x[1])), versions))

        assert len(context_list) == len(check_versions)

        for i, ctx in enumerate(sorted(context_list, key=lambda x: x.function())):
            assert ctx.function() == check_versions[i]


class CheckVersionIf:
    """
    Checks @version_if parametrization.
    """
    def check_common(self):  # pylint: disable=R0201
        """
        Check common scenarios with @ignite_versions parametrization.
        """
        @version_if(lambda ver: ver != V_2_8_0, variable_name='ver')
        @ignite_versions(str(DEV_BRANCH), str(V_2_8_0), version_prefix='ver')
        def function_1(ver):
            return IgniteVersion(ver)

        @version_if(lambda ver: ver > V_2_7_6, variable_name='ver_1')
        @version_if(lambda ver: ver < V_2_8_0, variable_name='ver_2')
        @ignite_versions((str(V_2_8_1), str(V_2_8_0)), (str(V_2_8_0), str(V_2_7_6)), version_prefix='ver')
        def function_2(ver_1, ver_2):
            return IgniteVersion(ver_1), IgniteVersion(ver_2)

        @ignite_versions(str(DEV_BRANCH), str(V_2_8_0))
        def function_3(ignite_version):
            return IgniteVersion(ignite_version)

        context_list = expand_function(func=function_1, sess_ctx=mock_session_ctx())
        context_list += expand_function(func=function_2, sess_ctx=mock_session_ctx())
        context_list += expand_function(func=function_3, sess_ctx=mock_session_ctx())

        assert len(context_list) == 6

        assert next(filter(lambda x: x.injected_args['ver'] == str(V_2_8_0), context_list)).ignore
        assert not next(filter(lambda x: x.injected_args['ver'] == str(DEV_BRANCH), context_list)).ignore
