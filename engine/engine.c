/**
 * AeroTax Calculation Engine (engine.c)
 * ======================================
 * High-performance, thread-safe C library for financial data processing.
 * Implements Indian tax slab calculations and statistical anomaly detection.
 *
 * Compile (Linux/Mac):
 *   gcc -O3 -march=native -ffast-math -shared -fPIC -o engine.so engine.c -lm -lpthread
 *
 * Compile (Windows):
 *   gcc -O3 -shared -o engine.dll engine.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>

/* -------------------------------------------------------------------------
 * SECTION 1: INDIAN TAX SLAB CONSTANTS (FY 2024-25 New Regime)
 * ------------------------------------------------------------------------- */

#define REBATE_LIMIT    700000.0   /* Section 87A: Full rebate up to ₹7L income */
#define SURCHARGE_10    5000000.0  /* 10% surcharge above ₹50L */
#define SURCHARGE_15   10000000.0  /* 15% surcharge above ₹1Cr */
#define CESS_RATE           0.04   /* 4% Health & Education Cess */

typedef struct {
    double lower;
    double upper;
    double rate;
} TaxSlab;

/* New Tax Regime Slabs (FY 2024-25) */
static const TaxSlab NEW_REGIME_SLABS[] = {
    {0.0,      300000.0,  0.00},
    {300000.0, 600000.0,  0.05},
    {600000.0, 900000.0,  0.10},
    {900000.0, 1200000.0, 0.15},
    {1200000.0,1500000.0, 0.20},
    {1500000.0, -1.0,     0.30}   /* -1 means "no upper limit" */
};
static const int NUM_SLABS = 6;

/* -------------------------------------------------------------------------
 * SECTION 2: TAX LIABILITY CALCULATION
 * ------------------------------------------------------------------------- */

/**
 * calculate_tax_liability()
 * Calculates net tax payable using Indian New Tax Regime slabs.
 *
 * @param income      Gross annual income in INR
 * @param deductions  Total deductions (Section 80C, 80D, HRA, etc.) in INR
 * @return            Net tax payable after cess (0.0 if rebate applies)
 */
double calculate_tax_liability(double income, double deductions) {
    if (income <= 0.0) return 0.0;

    /* Step 1: Compute taxable income */
    double taxable_income = income - deductions;
    if (taxable_income < 0.0) taxable_income = 0.0;

    /* Step 2: Standard deduction of ₹75,000 (Budget 2024) */
    taxable_income -= 75000.0;
    if (taxable_income < 0.0) taxable_income = 0.0;

    /* Step 3: Calculate base tax from slabs */
    double base_tax = 0.0;
    for (int i = 0; i < NUM_SLABS; i++) {
        double upper = (NEW_REGIME_SLABS[i].upper == -1.0)
                       ? taxable_income
                       : NEW_REGIME_SLABS[i].upper;

        if (taxable_income <= NEW_REGIME_SLABS[i].lower) break;

        double slab_income = (taxable_income < upper ? taxable_income : upper)
                             - NEW_REGIME_SLABS[i].lower;
        base_tax += slab_income * NEW_REGIME_SLABS[i].rate;
    }

    /* Step 4: Section 87A Rebate — zero tax if taxable income ≤ ₹7L */
    if (taxable_income <= REBATE_LIMIT) {
        return 0.0;
    }

    /* Step 5: Surcharge */
    double surcharge = 0.0;
    if (income > SURCHARGE_15) {
        surcharge = base_tax * 0.15;
    } else if (income > SURCHARGE_10) {
        surcharge = base_tax * 0.10;
    }

    /* Step 6: Health & Education Cess @ 4% */
    double total_before_cess = base_tax + surcharge;
    double cess = total_before_cess * CESS_RATE;

    return total_before_cess + cess;
}

/* -------------------------------------------------------------------------
 * SECTION 3: OLD REGIME TAX CALCULATION
 * ------------------------------------------------------------------------- */

/**
 * calculate_tax_old_regime()
 * Calculates tax under old regime (with deductions like 80C, 80D, HRA).
 *
 * @param income      Gross annual income in INR
 * @param deductions  Total allowable deductions in INR
 * @return            Net tax payable
 */
double calculate_tax_old_regime(double income, double deductions) {
    double taxable_income = income - deductions;
    if (taxable_income <= 250000.0) return 0.0;

    double base_tax = 0.0;

    if (taxable_income <= 500000.0) {
        base_tax = (taxable_income - 250000.0) * 0.05;
    } else if (taxable_income <= 1000000.0) {
        base_tax = 12500.0 + (taxable_income - 500000.0) * 0.20;
    } else {
        base_tax = 112500.0 + (taxable_income - 1000000.0) * 0.30;
    }

    /* Section 87A rebate for old regime (income ≤ ₹5L) */
    if (taxable_income <= 500000.0) return 0.0;

    double cess = base_tax * CESS_RATE;
    return base_tax + cess;
}

/* -------------------------------------------------------------------------
 * SECTION 4: STATISTICAL ANOMALY DETECTION (THREAD-SAFE)
 * ------------------------------------------------------------------------- */

/**
 * AnomalyResult: Returned by detect_outliers()
 * Caller must free() the `flags` array when done.
 */
typedef struct {
    int*   flags;        /* 1 = anomaly, 0 = normal (length = size) */
    int    count;        /* Total number of flagged anomalies */
    double mean;         /* Mean of the input array */
    double std_dev;      /* Standard deviation of the input array */
} AnomalyResult;

/* Internal mutex for thread safety on shared state */
static pthread_mutex_t anomaly_mutex = PTHREAD_MUTEX_INITIALIZER;

/**
 * detect_outliers()
 * Flags transactions deviating more than `threshold` standard deviations
 * from the mean. Default financial fraud threshold: 3.0 sigma.
 *
 * Algorithm: Two-pass Welford's online algorithm for numerical stability.
 *
 * @param transactions  Pointer to array of transaction amounts
 * @param size          Number of transactions
 * @param threshold     Sigma threshold (e.g., 3.0 for 99.7% confidence)
 * @return              AnomalyResult struct (caller must free flags)
 */
AnomalyResult detect_outliers(double* transactions, int size, double threshold) {
    AnomalyResult result = {NULL, 0, 0.0, 0.0};

    if (!transactions || size <= 0) return result;

    /* Allocate flags array */
    result.flags = (int*)calloc(size, sizeof(int));
    if (!result.flags) return result;

    /* Pass 1: Compute mean (Kahan compensated summation for precision) */
    double sum = 0.0, comp = 0.0;
    for (int i = 0; i < size; i++) {
        double y = transactions[i] - comp;
        double t = sum + y;
        comp = (t - sum) - y;
        sum = t;
    }
    double mean = sum / (double)size;

    /* Pass 2: Compute variance (Bessel's correction for sample std dev) */
    double sq_sum = 0.0;
    for (int i = 0; i < size; i++) {
        double diff = transactions[i] - mean;
        sq_sum += diff * diff;
    }
    double std_dev = (size > 1) ? sqrt(sq_sum / (double)(size - 1)) : 0.0;

    /* Thread-safe flag writing */
    pthread_mutex_lock(&anomaly_mutex);
    int count = 0;
    for (int i = 0; i < size; i++) {
        double z_score = (std_dev > 1e-9) ? fabs(transactions[i] - mean) / std_dev : 0.0;
        if (z_score > threshold) {
            result.flags[i] = 1;
            count++;
        }
    }
    result.count  = count;
    result.mean   = mean;
    result.std_dev = std_dev;
    pthread_mutex_unlock(&anomaly_mutex);

    return result;
}

/**
 * free_anomaly_result()
 * Convenience function to free heap memory from AnomalyResult.
 */
void free_anomaly_result(AnomalyResult* result) {
    if (result && result->flags) {
        free(result->flags);
        result->flags = NULL;
    }
}

/* -------------------------------------------------------------------------
 * SECTION 5: CTYPES-FRIENDLY FLAT API (no structs across FFI boundary)
 * These are the functions Python ctypes will call directly.
 * ------------------------------------------------------------------------- */

/**
 * py_calculate_tax()
 * Flat C function for Python ctypes. Returns net tax as double.
 */
double py_calculate_tax(double income, double deductions) {
    return calculate_tax_liability(income, deductions);
}

/**
 * py_detect_outliers()
 * Flat C function for Python ctypes.
 * Writes 1/0 into the `out_flags` array (pre-allocated by Python).
 * Returns number of anomalies found.
 *
 * @param transactions  Input array of doubles
 * @param size          Length of input array
 * @param threshold     Z-score threshold (3.0 recommended)
 * @param out_flags     Pre-allocated int array of length `size`
 * @param out_mean      Pointer to write mean value
 * @param out_std       Pointer to write std deviation value
 */
int py_detect_outliers(double* transactions, int size, double threshold,
                        int* out_flags, double* out_mean, double* out_std) {
    AnomalyResult r = detect_outliers(transactions, size, threshold);
    if (!r.flags) return -1;

    memcpy(out_flags, r.flags, size * sizeof(int));
    if (out_mean) *out_mean = r.mean;
    if (out_std)  *out_std  = r.std_dev;
    int count = r.count;
    free_anomaly_result(&r);
    return count;
}

/**
 * py_compare_regimes()
 * Returns 1 if new regime is better, 0 if old regime is better.
 * Writes both tax amounts to out_new and out_old.
 */
int py_compare_regimes(double income, double deductions,
                        double* out_new, double* out_old) {
    double new_tax = calculate_tax_liability(income, deductions);
    double old_tax = calculate_tax_old_regime(income, deductions);
    if (out_new) *out_new = new_tax;
    if (out_old) *out_old = old_tax;
    return (new_tax <= old_tax) ? 1 : 0;
}
