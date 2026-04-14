/**
 * AeroTax Calculation Engine (engine.c)
 * ======================================
 * Indian tax slab calculation + statistical anomaly detection.
 *
 * ZERO external includes. All standard functions declared manually.
 * The linker resolves them from the C runtime — no headers needed.
 *
 * Compile - Windows:
 *   gcc -O2 -std=c99 -shared -o engine.dll engine.c
 *
 * Compile - Linux/Mac:
 *   gcc -O2 -std=c99 -shared -fPIC -o engine.so engine.c
 */

/* ==========================================================================
 * SECTION 0: MANUAL RUNTIME DECLARATIONS  (replaces all #include)
 * The linker always finds these in the C runtime (msvcrt / glibc).
 * ========================================================================== */

typedef unsigned long long aero_size;

void *malloc (aero_size size);
void  free   (void *ptr);
void *memcpy (void *dst, const void *src, aero_size n);
void *memset (void *dst, int c, aero_size n);

/* calloc = malloc + memset */
static void *aero_calloc(int n, aero_size elem)
{
    aero_size total = (aero_size)n * elem;
    void *p = malloc(total);
    if (p) memset(p, 0, total);
    return p;
}

/* ==========================================================================
 * SECTION 1: DLL EXPORT
 * ========================================================================== */

#ifdef _WIN32
    #define AERO_API __declspec(dllexport)
#else
    #define AERO_API
#endif

/* ==========================================================================
 * SECTION 2: MATH HELPERS  (no math.h)
 * ========================================================================== */

static double aero_fabs(double x)
{
    return (x < 0.0) ? -x : x;
}

static double aero_sqrt(double n)
{
    double x, y;
    int i;
    if (n <= 0.0) return 0.0;
    x = n;
    for (i = 0; i < 64; i++) {
        y = 0.5 * (x + n / x);
        if (y >= x) break;
        x = y;
    }
    return x;
}

/* ==========================================================================
 * SECTION 3: TAX CONSTANTS  (FY 2024-25, amounts in INR)
 * ========================================================================== */

#define NUM_SLABS       6
#define REBATE_LIMIT    700000.0
#define SURCHARGE_10   5000000.0
#define SURCHARGE_15  10000000.0
#define CESS_RATE           0.04
#define STD_DEDUCTION   75000.0

typedef struct { double lower; double upper; double rate; } TaxSlab;

static const TaxSlab SLABS[NUM_SLABS] = {
    {      0.0,  300000.0, 0.00 },
    { 300000.0,  600000.0, 0.05 },
    { 600000.0,  900000.0, 0.10 },
    { 900000.0, 1200000.0, 0.15 },
    {1200000.0, 1500000.0, 0.20 },
    {1500000.0,      -1.0, 0.30 }
};

/* ==========================================================================
 * SECTION 4: TAX CALCULATION
 * ========================================================================== */

static double base_tax_from_slabs(double taxable)
{
    double tax = 0.0;
    int i;
    for (i = 0; i < NUM_SLABS; i++) {
        double upper, chunk;
        if (taxable <= SLABS[i].lower) break;
        upper = (SLABS[i].upper < 0.0) ? taxable : SLABS[i].upper;
        chunk = (taxable < upper ? taxable : upper) - SLABS[i].lower;
        tax  += chunk * SLABS[i].rate;
    }
    return tax;
}

static double add_cess(double base, double gross)
{
    double s = 0.0, total;
    if      (gross > SURCHARGE_15) s = base * 0.15;
    else if (gross > SURCHARGE_10) s = base * 0.10;
    total = base + s;
    return total + total * CESS_RATE;
}

static double new_regime_tax(double income, double deductions)
{
    double taxable;
    if (income <= 0.0) return 0.0;
    taxable = income - deductions - STD_DEDUCTION;
    if (taxable < 0.0) taxable = 0.0;
    if (taxable <= REBATE_LIMIT) return 0.0;
    return add_cess(base_tax_from_slabs(taxable), income);
}

static double old_regime_tax(double income, double deductions)
{
    double taxable = income - deductions;
    double base    = 0.0;
    if (taxable <= 250000.0) return 0.0;
    if      (taxable <= 500000.0)  base = (taxable - 250000.0) * 0.05;
    else if (taxable <= 1000000.0) base = 12500.0  + (taxable - 500000.0)  * 0.20;
    else                           base = 112500.0 + (taxable - 1000000.0) * 0.30;
    if (taxable <= 500000.0) return 0.0;
    return add_cess(base, income);
}

/* ==========================================================================
 * SECTION 5: ANOMALY DETECTION
 * ========================================================================== */

static int *detect_outliers(double *arr, int n, double thresh,
                             double *out_mean, double *out_std, int *out_count)
{
    double sum, comp, mean, sq_sum, std_dev;
    int *flags;
    int  i, count;

    *out_count = 0;
    *out_mean  = 0.0;
    *out_std   = 0.0;

    if (!arr || n <= 0) return 0;

    flags = (int *)aero_calloc(n, sizeof(int));
    if (!flags) return 0;

    /* Kahan-compensated mean */
    sum = 0.0; comp = 0.0;
    for (i = 0; i < n; i++) {
        double y = arr[i] - comp;
        double t = sum + y;
        comp = (t - sum) - y;
        sum  = t;
    }
    mean = sum / (double)n;

    /* Sample std deviation with Bessel's correction */
    sq_sum = 0.0;
    for (i = 0; i < n; i++) {
        double d = arr[i] - mean;
        sq_sum += d * d;
    }
    std_dev = (n > 1) ? aero_sqrt(sq_sum / (double)(n - 1)) : 0.0;

    count = 0;
    for (i = 0; i < n; i++) {
        double z = (std_dev > 1e-9) ? aero_fabs(arr[i] - mean) / std_dev : 0.0;
        if (z > thresh) { flags[i] = 1; count++; }
    }

    *out_mean  = mean;
    *out_std   = std_dev;
    *out_count = count;
    return flags;
}

/* ==========================================================================
 * SECTION 6: PUBLIC API  (Python ctypes entry points)
 * ========================================================================== */

AERO_API double py_calculate_tax(double income, double deductions)
{
    return new_regime_tax(income, deductions);
}

AERO_API int py_detect_outliers(double *transactions, int size,
                                double  threshold,
                                int    *out_flags,
                                double *out_mean,
                                double *out_std)
{
    double mean = 0.0, std = 0.0;
    int    count = 0, i;
    int   *flags = detect_outliers(transactions, size, threshold,
                                   &mean, &std, &count);
    if (!flags) return -1;

    for (i = 0; i < size; i++) out_flags[i] = flags[i];
    if (out_mean) *out_mean = mean;
    if (out_std)  *out_std  = std;
    free(flags);
    return count;
}

AERO_API int py_compare_regimes(double  income,   double  deductions,
                                double *out_new,  double *out_old)
{
    double n = new_regime_tax(income, deductions);
    double o = old_regime_tax(income, deductions);
    if (out_new) *out_new = n;
    if (out_old) *out_old = o;
    return (n <= o) ? 1 : 0;
}
