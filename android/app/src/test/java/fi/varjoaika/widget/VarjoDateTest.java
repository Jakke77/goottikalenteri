package fi.varjoaika.widget;
import org.junit.Test;
import static org.junit.Assert.*;
import java.util.Calendar;
import java.util.GregorianCalendar;
import java.util.TimeZone;
public class VarjoDateTest {
    private Calendar date(int y,int m,int d,String zone) {
        Calendar c=new GregorianCalendar(TimeZone.getTimeZone(zone)); c.clear(); c.set(y,m-1,d,12,0);return c;
    }
    @Test public void anchorAndBeforeEpoch() {
        VarjoDate d=VarjoDate.from(date(2026,10,4,"Europe/Helsinki"));
        assertEquals(1,d.year);assertEquals(0,d.month);assertEquals(6,d.day);assertEquals(6,d.weekday);
        assertEquals("Hornasunnuntai · Päivä 6\n0. Varjojenkuu",d.dateLabel());
        assertEquals("4. lokakuuta 2026",VarjoDate.official(date(2026,10,4,"Europe/Helsinki")));
        assertNull(VarjoDate.from(date(2026,9,27,"UTC")));
    }
    @Test public void fixedDaysAcrossDstAndYearBoundary() {
        VarjoDate a=VarjoDate.from(date(2026,10,25,"Europe/Helsinki"));
        VarjoDate b=VarjoDate.from(date(2026,10,26,"Europe/Helsinki"));assertEquals(a.day+1,b.day);
        VarjoDate next=VarjoDate.from(date(2027,10,23,"UTC"));
        assertEquals(2,next.year); assertEquals(0,next.month);assertEquals(0,next.day);
    }
}
