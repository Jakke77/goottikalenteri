package fi.varjoaika.widget;
import java.util.Calendar;
import java.util.GregorianCalendar;
import java.util.Locale;
import java.util.TimeZone;

public final class VarjoDate {
    public static final String[] MONTHS = {"Varjojenkuu", "Hallankuu", "Routakuu", "Korppikuu", "Hylättyjen kuu", "Kalmistonkuu", "Ikiyön kuu", "Verikuu", "Pimentojen kuu", "Kuihtumisen kuu", "Aaveiden kuu", "Marraskuu", "Sielunkuu"};
    public static final String[] WEEKDAYS = {"Varjomaanantai", "Kallotiistai", "Ruumiskeskiviikko", "Kalmistotorstai", "Kryptaperjantai", "Noitalauantai", "Hornasunnuntai"};
    private static final String[] OFFICIAL = {"tammikuuta", "helmikuuta", "maaliskuuta", "huhtikuuta", "toukokuuta", "kesäkuuta", "heinäkuuta", "elokuuta", "syyskuuta", "lokakuuta", "marraskuuta", "joulukuuta"};
    public final long year;
    public final int month, day, weekday;
    private VarjoDate(long offset) {
        year = offset / 390 + 1; month = (int)(offset % 390 / 30);
        day = (int)(offset % 30); weekday = (int)(offset % 7);
    }
    private static long midnight(int year, int month, int day) {
        Calendar c = new GregorianCalendar(TimeZone.getTimeZone("UTC"), Locale.ROOT);
        c.clear(); c.set(year, month, day); return c.getTimeInMillis();
    }
    public static VarjoDate from(Calendar local) {
        long days = (midnight(local.get(Calendar.YEAR), local.get(Calendar.MONTH), local.get(Calendar.DAY_OF_MONTH)) - midnight(2026, 8, 28)) / 86400000L;
        return days < 0 ? null : new VarjoDate(days);
    }
    public static String official(Calendar now) {
        return now.get(Calendar.DAY_OF_MONTH) + ". " + OFFICIAL[now.get(Calendar.MONTH)] + " " + now.get(Calendar.YEAR);
    }
    public String dateLabel() { return WEEKDAYS[weekday] + " · Päivä " + day + "\n" + month + ". " + MONTHS[month]; }
    public String yearLabel() { return String.format(Locale.ROOT, "Varjoaika · Vuosi %04d", year); }
}
