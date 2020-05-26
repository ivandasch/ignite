/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.ignite.platform;

import java.util.UUID;
import org.apache.ignite.Ignite;
import org.apache.ignite.compute.ComputeJobAdapter;
import org.apache.ignite.internal.processors.platform.PlatformNativeException;
import org.apache.ignite.internal.processors.platform.services.PlatformService;
import org.apache.ignite.resources.IgniteInstanceResource;
import org.apache.ignite.testframework.GridTestUtils;

/**
 *  Basic task to calling {@link PlatformService} from Java.
 */
public class PlatformServiceCallTask extends AbstractPlatformServiceCallTask {
    /** {@inheritDoc} */
    @Override ComputeJobAdapter createJob(String svcName) {
        return new PlatformServiceCallJob(svcName);
    }

    /** */
    static class PlatformServiceCallJob extends AbstractServiceCallJob {
        /** */
        @SuppressWarnings("unused")
        @IgniteInstanceResource
        private transient Ignite ignite;

        /**
         * @param srvcName Service name.
         */
        PlatformServiceCallJob(String srvcName) {
            super(srvcName);
        }

        /** {@inheritDoc} */
        @Override void runTest() {
            TestPlatformService srv = ignite.services().serviceProxy(srvcName, TestPlatformService.class, false);

            {
                UUID nodeId = srv.getNodeId();
                assertTrue(ignite.cluster().nodes().stream().anyMatch(n -> n.id().equals(nodeId)));
            }

            {
                UUID expUuid = UUID.randomUUID();
                srv.setGuidProp(expUuid);
                assertEquals(expUuid, srv.getGuidProp());
            }

            {
                TestValue exp = new TestValue(1, "test");
                srv.setValueProp(exp);
                assertEquals(exp, srv.getValueProp());
            }

            {
                PlatformNativeException nativeEx = (PlatformNativeException)GridTestUtils
                        .assertThrowsWithCause(srv::errorMethod, PlatformNativeException.class)
                        .getCause();

                assertTrue(nativeEx.toString().contains("Failed method"));
            }
        }
    }
}
