package fi.varjoaika.widget;
import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.graphics.Color;
import android.widget.*;
import java.util.LinkedHashMap;
import java.util.Map;

public class SettingsActivity extends Activity {
    private final Map<String, SeekBar> sliders = new LinkedHashMap<>();
    private LinearLayout content;
    private SharedPreferences prefs;
    private void label(String text) {
        TextView t = new TextView(this); t.setText(text); t.setTextColor(Color.rgb(219,230,239)); t.setTextSize(16); content.addView(t);
    }
    private void slider(String key, String title, int value, int min, int max) {
        TextView titleView = new TextView(this); titleView.setTextColor(Color.rgb(37,197,255));
        content.addView(titleView);
        SeekBar s = new SeekBar(this); s.setMax(max-min); s.setProgress(prefs.getInt(key,value)-min); s.setTag(min);
        titleView.setText(title+": "+(s.getProgress()+min));
        s.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar b,int p,boolean user) { titleView.setText(title+": "+(p+min)); }
            public void onStartTrackingTouch(SeekBar b) {} public void onStopTrackingTouch(SeekBar b) {}
        });
        content.addView(s); sliders.put(key,s);
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); prefs=VarjoWidget.prefs(this);
        ScrollView scroll=new ScrollView(this); content=new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL);
        int pad=(int)(20*getResources().getDisplayMetrics().density); content.setPadding(pad,pad,pad,pad);
        scroll.addView(content); setContentView(scroll);
        scroll.setOnApplyWindowInsetsListener((view,insets)-> { view.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom()); return insets; });
        scroll.requestApplyInsets();
        label("VARJOAIKA — widgetin asetukset");
        label("Lisää widget kotinäyttöön: paina tyhjää kohtaa pitkään → Widgetit → Varjoaika. Siirrä ja muuta kokoa kotinäytön tavallisilla eleillä. Napauta widgetiä avataksesi nämä asetukset.");
        slider("clock_size","Kellon koko (sp)",40,18,72);
        slider("date_size","Goottipäivämäärän koko (sp)",16,10,32);
        slider("year_size","Vuosiluvun koko (sp)",13,10,28);
        slider("official_size","Virallisen päivämäärän koko (sp)",11,9,24);
        slider("opacity","Tekstin peittävyys (%)",100,30,100);
        label("Fontti"); Spinner font=new Spinner(this);
        font.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Sans","Serif","Monospace"}));
        font.setSelection(prefs.getInt("font",0)); content.addView(font);
        CheckBox seconds=new CheckBox(this); seconds.setText("Näytä sekunnit"); seconds.setChecked(prefs.getBoolean("seconds",true)); content.addView(seconds);
        Button save=new Button(this); save.setText("Tallenna"); content.addView(save);
        save.setOnClickListener(v->{ SharedPreferences.Editor edit=prefs.edit();
            for (Map.Entry<String,SeekBar> entry:sliders.entrySet()) edit.putInt(entry.getKey(),entry.getValue().getProgress()+(Integer)entry.getValue().getTag());
            edit.putInt("font",font.getSelectedItemPosition()).putBoolean("seconds",seconds.isChecked()).apply();
            VarjoWidget.updateAll(this); Toast.makeText(this,"Widget päivitetty",Toast.LENGTH_SHORT).show(); finish();
        });
        Button refresh=new Button(this); refresh.setText("Päivitä päivämäärä nyt"); content.addView(refresh);
        refresh.setOnClickListener(v->{VarjoWidget.updateAll(this);Toast.makeText(this,"Päivämäärä päivitetty",Toast.LENGTH_SHORT).show();});
        label("Kello käyttää puhelimen järjestelmäaikaa. Pidä Androidin automaattinen aika päällä. Päivämäärän päivitys voi viivästyä virransäästössä; yllä oleva painike päivittää sen heti. Asetukset koskevat kaikkia Varjoaika-widgetejä.");
    }
}
