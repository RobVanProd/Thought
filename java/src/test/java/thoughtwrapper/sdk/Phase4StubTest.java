package thoughtwrapper.sdk;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

class Phase4StubTest {

    @Test
    void statusMentionsPhase4() {
        String status = Phase4Stub.status();
        Assertions.assertTrue(status.contains("phase4"));
        Assertions.assertTrue(status.contains("stub"));
    }
}
