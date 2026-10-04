package fi.varjoaika.widget;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Calendar;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/** One-hour, network-aware updates; Android may defer jobs during battery saving. */
public class WeatherJob extends JobService {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private Future<?> pending;
    static String location(SharedPreferences p) {
        return p.getBoolean("weather_auto", true) ? "" : p.getString("weather_city", "").trim();
    }
    static void schedule(Context c, boolean force) {
        JobScheduler scheduler = (JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        SharedPreferences p = VarjoWidget.prefs(c);
        int count = android.appwidget.AppWidgetManager.getInstance(c).getAppWidgetIds(new ComponentName(c,VarjoWidget.class)).length;
        if (!p.getBoolean("weather_enabled",false) || count==0 || (!p.getBoolean("weather_auto",true) && location(p).isEmpty())) {
            scheduler.cancel(27); scheduler.cancel(28); return;
        }
        ComponentName component = new ComponentName(c,WeatherJob.class);
        boolean hasPeriodic=false;
        for(JobInfo job:scheduler.getAllPendingJobs())if(job.getId()==27)hasPeriodic=true;
        if(!hasPeriodic) scheduler.schedule(new JobInfo.Builder(27,component).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPeriodic(3600000).setPersisted(true).build());
        if(force) scheduler.schedule(new JobInfo.Builder(28,component).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setMinimumLatency(0).build());
    }
    static String forecast(JSONObject data) throws Exception {
        JSONObject area=data.getJSONArray("nearest_area").getJSONObject(0);
        StringBuilder text=new StringBuilder(area.getJSONArray("areaName").getJSONObject(0).getString("value"));
        JSONArray days=data.getJSONArray("weather"); int count=0;
        Calendar now=Calendar.getInstance();
        String today=String.format(java.util.Locale.ROOT,"%04d-%02d-%02d",now.get(Calendar.YEAR),now.get(Calendar.MONTH)+1,now.get(Calendar.DAY_OF_MONTH));
        for(int i=0;i<days.length() && count<3;i++) {
            JSONObject d=days.getJSONObject(i); String date=d.getString("date"); if(date.compareTo(today)<0)continue;
            JSONArray hours=d.getJSONArray("hourly"); JSONObject noon=null; int distance=Integer.MAX_VALUE,rain=0;
            for(int j=0;j<hours.length();j++) {
                JSONObject h=hours.getJSONObject(j); int delta=Math.abs(h.optInt("time",0)-1200);
                if(delta<distance){noon=h;distance=delta;} rain=Math.max(rain,h.optInt("chanceofrain",0));
            }
            String description="";
            if(noon!=null){JSONArray desc=noon.optJSONArray("lang_fi");if(desc==null)desc=noon.optJSONArray("weatherDesc");if(desc!=null && desc.length()>0)description=desc.getJSONObject(0).optString("value");}
            String[] parts=date.split("-");
            text.append("\n").append(Integer.parseInt(parts[2])).append('.').append(Integer.parseInt(parts[1])).append(".  ")
                .append(d.getString("mintempC")).append('…').append(d.getString("maxtempC")).append(" °C · ")
                .append(description).append(" · sade ").append(rain).append(" %");count++;
        }
        if(count==0)throw new IllegalArgumentException("Ennuste vanhentunut");return text.toString();
    }
    static String text(SharedPreferences p) {
        if(!p.getBoolean("weather_enabled",false))return "";
        if(!p.getBoolean("weather_auto",true) && location(p).isEmpty())return "Anna sään paikkakunta asetuksissa.";
        if(!location(p).equals(p.getString("weather_key",null)))return "Säätä haetaan…\nwttr.in";
        try {
            String text=forecast(new JSONObject(p.getString("weather_data","{}")));
            long age=Math.max(0,(System.currentTimeMillis()-p.getLong("weather_saved",0))/60000);
            return text+"\nwttr.in · päivitetty "+age+" min sitten"+(p.getBoolean("weather_error",false)?" · yhteys epäonnistui":"");
        } catch(Exception e){return "Säätä ei saatu. Tarkista paikkakunta ja yhteys.\nwttr.in";}
    }
    @Override public boolean onStartJob(JobParameters params) {
        pending=executor.submit(()-> {
            SharedPreferences p=VarjoWidget.prefs(this);String key=location(p);HttpURLConnection connection=null;
            try {
                if(!p.getBoolean("weather_enabled",false))return;
                boolean fresh=key.equals(p.getString("weather_key",null)) && System.currentTimeMillis()-p.getLong("weather_saved",0)<3600000;
                if(params.getJobId()==27 && fresh)return;
                connection=(HttpURLConnection)new URL("https://wttr.in/"+URLEncoder.encode(key,"UTF-8")+"?format=j1&lang=fi").openConnection();
                connection.setConnectTimeout(20000);connection.setReadTimeout(20000);connection.setRequestProperty("User-Agent","Varjoaika/0.5.0");
                if(connection.getResponseCode()!=200)throw new IllegalStateException("Sääpalvelun virhe");
                ByteArrayOutputStream buffer=new ByteArrayOutputStream();
                try(InputStream in=connection.getInputStream()) {
                    byte[] chunk=new byte[4096];int n;
                    while((n=in.read(chunk))!=-1){buffer.write(chunk,0,n);if(buffer.size()>1048576)throw new IllegalStateException("Liian suuri vastaus");}
                }
                String json=new String(buffer.toByteArray(),StandardCharsets.UTF_8);forecast(new JSONObject(json));
                if(key.equals(location(p)) && p.getBoolean("weather_enabled",false))p.edit().putString("weather_data",json).putString("weather_key",key).putLong("weather_saved",System.currentTimeMillis()).putBoolean("weather_error",false).apply();
            }catch(Exception e){if(key.equals(location(p)))p.edit().putBoolean("weather_error",true).apply();}
            finally{if(connection!=null)connection.disconnect();VarjoWidget.renderAll(this);jobFinished(params,false);}
        });return true;
    }
    @Override public boolean onStopJob(JobParameters params){if(pending!=null)pending.cancel(true);return true;}
    @Override public void onDestroy(){executor.shutdownNow();super.onDestroy();}
}
