package org.claritylink.android;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.FrameLayout;

/** Keeps the diagnostic process non-empty while the tested Activity finishes. */
public final class R7C7LifecycleGuardActivity extends Activity {
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new FrameLayout(this));
        Intent request=getIntent();
        Intent target=new Intent(this,R7C2RuntimeActivity.class);
        String focused=request.getStringExtra("r7c6Case");
        if(focused!=null)target.putExtra("r7c6Case",focused);
        target.putExtra("r7c7Repeat",request.getIntExtra("r7c7Repeat",1));
        String r7dMode=request.getStringExtra("r7dMode");
        if(r7dMode!=null) {
            target.putExtra("r7dMode",r7dMode);
            target.putExtra("r7dMinutes",request.getIntExtra("r7dMinutes",30));
            target.putExtra("r7dFps",request.getIntExtra("r7dFps",30));
        }
        startActivity(target);
    }
}
