package fi.varjoaika.widget;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.TypedValue;
import android.widget.RemoteViews;
import java.util.Calendar;

public class VarjoWidget extends AppWidgetProvider {
    private static final String REFRESH = "fi.varjoaika.widget.REFRESH";
    static SharedPreferences prefs(Context c) { return c.getSharedPreferences("appearance", Context.MODE_PRIVATE); }
    public static void updateAll(Context c) {
        renderAll(c); WeatherJob.schedule(c, false);
    }
    public static void renderAll(Context c) {
        AppWidgetManager m = AppWidgetManager.getInstance(c);
        int[] ids = m.getAppWidgetIds(new ComponentName(c, VarjoWidget.class));
        for (int id : ids) update(c, m, id);
        AlarmManager alarms = (AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
        PendingIntent refresh = PendingIntent.getBroadcast(c, 0, new Intent(c, VarjoWidget.class).setAction(REFRESH), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        if (ids.length == 0) { alarms.cancel(refresh); return; }
        Calendar midnight = Calendar.getInstance();
        midnight.add(Calendar.DAY_OF_MONTH, 1); midnight.set(Calendar.HOUR_OF_DAY, 0);
        midnight.set(Calendar.MINUTE, 0); midnight.set(Calendar.SECOND, 0); midnight.set(Calendar.MILLISECOND, 0);
        // Inexact alarm avoids exact-alarm permissions; Android may defer during Doze.
        alarms.setAndAllowWhileIdle(AlarmManager.RTC, midnight.getTimeInMillis(), refresh);
    }
    private static void update(Context c, AppWidgetManager m, int id) {
        SharedPreferences p = prefs(c);
        int font = p.getInt("font", 0);
        int layout = font == 1 ? R.layout.widget_serif : font == 2 ? R.layout.widget_mono : R.layout.widget;
        RemoteViews v = new RemoteViews(c.getPackageName(), layout);
        Calendar now = Calendar.getInstance();
        VarjoDate date = VarjoDate.from(now);
        v.setTextViewText(R.id.gothic_date, date == null ? "Ennen Varjoajan alkua" : date.dateLabel());
        v.setTextViewText(R.id.gothic_year, date == null ? "Varjoaika" : date.yearLabel());
        v.setTextViewText(R.id.official, VarjoDate.official(now));
        v.setTextViewText(R.id.weather, WeatherJob.text(p));
        v.setViewVisibility(R.id.weather,p.getBoolean("weather_enabled",false)?android.view.View.VISIBLE:android.view.View.GONE);
        String format = p.getBoolean("seconds", true) ? "HH:mm:ss" : "HH:mm";
        v.setCharSequence(R.id.clock, "setFormat12Hour", format);
        v.setCharSequence(R.id.clock, "setFormat24Hour", format);
        int color = ((255 * p.getInt("opacity", 100) / 100) << 24) | 0x25c5ff;
        int[] views = {R.id.clock, R.id.gothic_date, R.id.gothic_year, R.id.official, R.id.weather};
        String[] keys = {"clock_size", "date_size", "year_size", "official_size", "weather_size"};
        int[] sizes = {40, 16, 13, 11, 11};
        for (int i = 0; i < views.length; i++) {
            v.setTextColor(views[i], color);
            v.setTextViewTextSize(views[i], TypedValue.COMPLEX_UNIT_SP, p.getInt(keys[i], sizes[i]));
        }
        PendingIntent settings = PendingIntent.getActivity(c, 0, new Intent(c, SettingsActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        v.setOnClickPendingIntent(R.id.widget_root, settings);
        m.updateAppWidget(id, v);
    }
    @Override public void onUpdate(Context c, AppWidgetManager m, int[] ids) { updateAll(c); if(System.currentTimeMillis()-prefs(c).getLong("weather_saved",0)>=3600000) WeatherJob.schedule(c,true); }
    @Override public void onAppWidgetOptionsChanged(Context c, AppWidgetManager m, int id, Bundle options) { updateAll(c); }
    @Override public void onDeleted(Context c, int[] ids) { updateAll(c); }
    @Override public void onDisabled(Context c) { updateAll(c); }
    @Override public void onReceive(Context c, Intent i) {
        super.onReceive(c, i);
        String a = i.getAction();
        if (REFRESH.equals(a) || Intent.ACTION_BOOT_COMPLETED.equals(a) || Intent.ACTION_TIME_CHANGED.equals(a) || Intent.ACTION_TIMEZONE_CHANGED.equals(a) || Intent.ACTION_DATE_CHANGED.equals(a)) updateAll(c);
    }
}
