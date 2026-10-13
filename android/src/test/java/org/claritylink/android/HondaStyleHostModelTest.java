package org.claritylink.android;

public final class HondaStyleHostModelTest {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        HondaStyleHostModel model = new HondaStyleHostModel();
        require(model.priorityRank(HondaStyleHostModel.Priority.BOTTOM_CONTENT) <
                model.priorityRank(HondaStyleHostModel.Priority.NAVIGATION_CONTENT), "navigation above bottom");
        require(model.priorityRank(HondaStyleHostModel.Priority.NAVIGATION_CONTENT) <
                model.priorityRank(HondaStyleHostModel.Priority.WARNING_INTERRUPT), "warning above navigation");
        require(!model.attach(0, true), "zero generation rejected");
        require(!model.attach(1, false), "already-parented view rejected");
        require(model.attach(1, true), "active navigation accepts one content view");
        require(!model.attach(2, true), "second content view rejected");
        model.setWarningVisible(true);
        require(!model.contentVisible() && model.contentGeneration() == 1,
                "warning preempts display while preserving same-session content");
        require(!model.attach(2, true), "new content rejected while warning active");
        require(!model.detach(2), "stale generation cannot detach current content");
        model.setWarningVisible(false);
        require(model.contentVisible(), "content resumes after simulated warning clears");
        model.setNavigationActive(false);
        require(!model.contentVisible() && model.contentGeneration() == 0,
                "navigation exit drops content and generation");
        model.setNavigationActive(true);
        require(!model.contentVisible(), "navigation re-entry does not restore stale content");
        require(model.attach(3, true), "new navigation generation can attach");
        require(model.detach(3), "matching generation detaches");
        model.close();
        model.close();
        require(model.isClosed() && !model.attach(4, true), "close is idempotent and rejects reattach");
        boolean mutationRejected = false;
        try { model.setWarningVisible(true); }
        catch (IllegalStateException expected) { mutationRejected = true; }
        require(mutationRejected, "closed model rejects mutation");

        for (int generation = 1; generation <= 100; generation++) {
            HondaStyleHostModel cycle = new HondaStyleHostModel();
            require(cycle.attach(generation, true), "cycle attach");
            cycle.setWarningVisible(true);
            require(!cycle.contentVisible(), "cycle warning blanks content");
            cycle.setNavigationActive(false);
            cycle.setNavigationActive(true);
            require(cycle.contentGeneration() == 0, "cycle clears generation on page exit");
            cycle.close();
        }
        System.out.println("HONDA_STYLE_HOST_MODEL_PASS cycles=100 priority=ordered warning=preempts");
    }
}
