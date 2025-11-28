/**
 * 经典排序算法大全 (Classic Sorting Algorithms Collection)
 * 
 * 本文件包含所有经典的排序算法实现
 * This file contains implementations of all classic sorting algorithms
 * 
 * 算法列表 (Algorithm List):
 * 1. 冒泡排序 (Bubble Sort)
 * 2. 选择排序 (Selection Sort)
 * 3. 插入排序 (Insertion Sort)
 * 4. 希尔排序 (Shell Sort)
 * 5. 归并排序 (Merge Sort)
 * 6. 快速排序 (Quick Sort)
 * 7. 堆排序 (Heap Sort)
 * 8. 计数排序 (Counting Sort)
 * 9. 基数排序 (Radix Sort)
 * 10. 桶排序 (Bucket Sort)
 */

#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// ==================== 1. 冒泡排序 (Bubble Sort) ====================
/**
 * 冒泡排序
 * 时间复杂度: O(n^2)
 * 空间复杂度: O(1)
 * 稳定性: 稳定
 */
void bubbleSort(vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        bool swapped = false;
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                swap(arr[j], arr[j + 1]);
                swapped = true;
            }
        }
        // 如果没有发生交换，说明已经有序
        if (!swapped) break;
    }
}

// ==================== 2. 选择排序 (Selection Sort) ====================
/**
 * 选择排序
 * 时间复杂度: O(n^2)
 * 空间复杂度: O(1)
 * 稳定性: 不稳定
 */
void selectionSort(vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[minIdx]) {
                minIdx = j;
            }
        }
        if (minIdx != i) {
            swap(arr[i], arr[minIdx]);
        }
    }
}

// ==================== 3. 插入排序 (Insertion Sort) ====================
/**
 * 插入排序
 * 时间复杂度: O(n^2)
 * 空间复杂度: O(1)
 * 稳定性: 稳定
 */
void insertionSort(vector<int>& arr) {
    int n = arr.size();
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}

// ==================== 4. 希尔排序 (Shell Sort) ====================
/**
 * 希尔排序 (缩小增量排序)
 * 时间复杂度: O(n log n) ~ O(n^2) 取决于间隔序列
 * 空间复杂度: O(1)
 * 稳定性: 不稳定
 */
void shellSort(vector<int>& arr) {
    int n = arr.size();
    // 使用希尔增量序列: n/2, n/4, ..., 1
    for (int gap = n / 2; gap > 0; gap /= 2) {
        for (int i = gap; i < n; i++) {
            int temp = arr[i];
            int j = i;
            while (j >= gap && arr[j - gap] > temp) {
                arr[j] = arr[j - gap];
                j -= gap;
            }
            arr[j] = temp;
        }
    }
}

// ==================== 5. 归并排序 (Merge Sort) ====================
/**
 * 归并排序 - 合并两个有序数组
 */
void merge(vector<int>& arr, int left, int mid, int right) {
    int n1 = mid - left + 1;
    int n2 = right - mid;
    
    vector<int> L(n1), R(n2);
    
    for (int i = 0; i < n1; i++)
        L[i] = arr[left + i];
    for (int j = 0; j < n2; j++)
        R[j] = arr[mid + 1 + j];
    
    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            arr[k] = L[i];
            i++;
        } else {
            arr[k] = R[j];
            j++;
        }
        k++;
    }
    
    while (i < n1) {
        arr[k] = L[i];
        i++;
        k++;
    }
    
    while (j < n2) {
        arr[k] = R[j];
        j++;
        k++;
    }
}

/**
 * 归并排序
 * 时间复杂度: O(n log n)
 * 空间复杂度: O(n)
 * 稳定性: 稳定
 */
void mergeSort(vector<int>& arr, int left, int right) {
    if (left < right) {
        int mid = left + (right - left) / 2;
        mergeSort(arr, left, mid);
        mergeSort(arr, mid + 1, right);
        merge(arr, left, mid, right);
    }
}

// 归并排序的包装函数
void mergeSort(vector<int>& arr) {
    if (arr.size() > 1) {
        mergeSort(arr, 0, arr.size() - 1);
    }
}

// ==================== 6. 快速排序 (Quick Sort) ====================
/**
 * 快速排序 - 分区函数
 */
int partition(vector<int>& arr, int low, int high) {
    int pivot = arr[high];
    int i = low - 1;
    
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {
            i++;
            swap(arr[i], arr[j]);
        }
    }
    swap(arr[i + 1], arr[high]);
    return i + 1;
}

/**
 * 快速排序
 * 时间复杂度: 平均 O(n log n), 最坏 O(n^2)
 * 空间复杂度: O(log n)
 * 稳定性: 不稳定
 */
void quickSort(vector<int>& arr, int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

// 快速排序的包装函数
void quickSort(vector<int>& arr) {
    if (arr.size() > 1) {
        quickSort(arr, 0, arr.size() - 1);
    }
}

// ==================== 7. 堆排序 (Heap Sort) ====================
/**
 * 堆排序 - 维护堆性质
 */
void heapify(vector<int>& arr, int n, int i) {
    int largest = i;
    int left = 2 * i + 1;
    int right = 2 * i + 2;
    
    if (left < n && arr[left] > arr[largest])
        largest = left;
    
    if (right < n && arr[right] > arr[largest])
        largest = right;
    
    if (largest != i) {
        swap(arr[i], arr[largest]);
        heapify(arr, n, largest);
    }
}

/**
 * 堆排序
 * 时间复杂度: O(n log n)
 * 空间复杂度: O(1)
 * 稳定性: 不稳定
 */
void heapSort(vector<int>& arr) {
    int n = arr.size();
    
    // 建立最大堆
    for (int i = n / 2 - 1; i >= 0; i--)
        heapify(arr, n, i);
    
    // 逐一取出堆顶元素
    for (int i = n - 1; i > 0; i--) {
        swap(arr[0], arr[i]);
        heapify(arr, i, 0);
    }
}

// ==================== 8. 计数排序 (Counting Sort) ====================
/**
 * 计数排序
 * 时间复杂度: O(n + k), k是数据范围
 * 空间复杂度: O(k)
 * 稳定性: 稳定
 * 注意: 支持正负整数排序
 */
void countingSort(vector<int>& arr) {
    if (arr.empty()) return;
    
    int maxVal = *max_element(arr.begin(), arr.end());
    int minVal = *min_element(arr.begin(), arr.end());
    int range = maxVal - minVal + 1;
    
    vector<int> count(range, 0);
    vector<int> output(arr.size());
    
    // 统计每个元素出现的次数
    for (int i = 0; i < (int)arr.size(); i++)
        count[arr[i] - minVal]++;
    
    // 计算累积计数
    for (int i = 1; i < range; i++)
        count[i] += count[i - 1];
    
    // 构建输出数组 (从后向前遍历保证稳定性)
    for (int i = arr.size() - 1; i >= 0; i--) {
        output[count[arr[i] - minVal] - 1] = arr[i];
        count[arr[i] - minVal]--;
    }
    
    // 复制回原数组
    for (int i = 0; i < (int)arr.size(); i++)
        arr[i] = output[i];
}

// ==================== 9. 基数排序 (Radix Sort) ====================
/**
 * 基数排序 - 按指定位数进行计数排序
 */
void countingSortByDigit(vector<int>& arr, int exp) {
    int n = arr.size();
    vector<int> output(n);
    vector<int> count(10, 0);
    
    // 统计每个数字出现的次数
    for (int i = 0; i < n; i++)
        count[(arr[i] / exp) % 10]++;
    
    // 计算累积计数
    for (int i = 1; i < 10; i++)
        count[i] += count[i - 1];
    
    // 构建输出数组
    for (int i = n - 1; i >= 0; i--) {
        output[count[(arr[i] / exp) % 10] - 1] = arr[i];
        count[(arr[i] / exp) % 10]--;
    }
    
    // 复制回原数组
    for (int i = 0; i < n; i++)
        arr[i] = output[i];
}

/**
 * 基数排序 (LSD - 最低位优先)
 * 时间复杂度: O(d * (n + k)), d是位数, k是基数(10)
 * 空间复杂度: O(n + k)
 * 稳定性: 稳定
 * 注意: 此实现仅适用于非负整数，负数会导致错误结果
 */
void radixSort(vector<int>& arr) {
    if (arr.empty()) return;
    
    int maxVal = *max_element(arr.begin(), arr.end());
    
    // 对每一位进行计数排序
    for (int exp = 1; maxVal / exp > 0; exp *= 10)
        countingSortByDigit(arr, exp);
}

// ==================== 10. 桶排序 (Bucket Sort) ====================
/**
 * 桶排序
 * 时间复杂度: 平均 O(n + k), 最坏 O(n^2)
 * 空间复杂度: O(n + k)
 * 稳定性: 稳定 (取决于桶内排序算法)
 */
void bucketSort(vector<int>& arr) {
    if (arr.empty()) return;
    
    int n = arr.size();
    int maxVal = *max_element(arr.begin(), arr.end());
    int minVal = *min_element(arr.begin(), arr.end());
    
    // 计算桶的数量和大小
    int bucketCount = n;
    double bucketSize = (double)(maxVal - minVal + 1) / bucketCount;
    if (bucketSize < 1) bucketSize = 1;
    
    // 创建桶
    vector<vector<int>> buckets(bucketCount);
    
    // 将元素分配到桶中
    for (int i = 0; i < n; i++) {
        int bucketIdx = (int)((arr[i] - minVal) / bucketSize);
        if (bucketIdx >= bucketCount) bucketIdx = bucketCount - 1;
        buckets[bucketIdx].push_back(arr[i]);
    }
    
    // 对每个桶进行排序 (使用std::sort)
    for (int i = 0; i < bucketCount; i++) {
        sort(buckets[i].begin(), buckets[i].end());
    }
    
    // 合并所有桶
    int index = 0;
    for (int i = 0; i < bucketCount; i++) {
        for (int j = 0; j < (int)buckets[i].size(); j++) {
            arr[index++] = buckets[i][j];
        }
    }
}

// ==================== 辅助函数 ====================
/**
 * 打印数组
 */
void printArray(const vector<int>& arr, const string& name) {
    cout << name << ": [";
    for (int i = 0; i < (int)arr.size(); i++) {
        cout << arr[i];
        if (i < (int)arr.size() - 1) cout << ", ";
    }
    cout << "]" << endl;
}

/**
 * 验证数组是否已排序
 */
bool isSorted(const vector<int>& arr) {
    for (int i = 1; i < (int)arr.size(); i++) {
        if (arr[i] < arr[i - 1]) return false;
    }
    return true;
}

// ==================== 测试函数 ====================
void testSortingAlgorithm(const string& name, void (*sortFunc)(vector<int>&)) {
    vector<int> arr = {64, 34, 25, 12, 22, 11, 90, 5, 77, 30};
    
    cout << "\n=== 测试 " << name << " ===" << endl;
    printArray(arr, "排序前");
    
    sortFunc(arr);
    
    printArray(arr, "排序后");
    cout << "排序结果: " << (isSorted(arr) ? "正确 ✓" : "错误 ✗") << endl;
}

int main() {
    cout << "========================================" << endl;
    cout << "    经典排序算法测试 (Classic Sorting Algorithms Test)" << endl;
    cout << "========================================" << endl;
    
    // 测试所有排序算法
    testSortingAlgorithm("冒泡排序 (Bubble Sort)", bubbleSort);
    testSortingAlgorithm("选择排序 (Selection Sort)", selectionSort);
    testSortingAlgorithm("插入排序 (Insertion Sort)", insertionSort);
    testSortingAlgorithm("希尔排序 (Shell Sort)", shellSort);
    testSortingAlgorithm("归并排序 (Merge Sort)", mergeSort);
    testSortingAlgorithm("快速排序 (Quick Sort)", quickSort);
    testSortingAlgorithm("堆排序 (Heap Sort)", heapSort);
    testSortingAlgorithm("计数排序 (Counting Sort)", countingSort);
    testSortingAlgorithm("基数排序 (Radix Sort)", radixSort);
    testSortingAlgorithm("桶排序 (Bucket Sort)", bucketSort);
    
    cout << "\n========================================" << endl;
    cout << "    所有排序算法测试完成!" << endl;
    cout << "========================================" << endl;
    
    // 排序算法复杂度总结
    cout << "\n排序算法复杂度总结 (Sorting Algorithm Complexity Summary):" << endl;
    cout << "-----------------------------------------------------------" << endl;
    cout << "算法名称\t\t时间复杂度(平均)\t空间复杂度\t稳定性" << endl;
    cout << "-----------------------------------------------------------" << endl;
    cout << "冒泡排序\t\tO(n^2)\t\t\tO(1)\t\t稳定" << endl;
    cout << "选择排序\t\tO(n^2)\t\t\tO(1)\t\t不稳定" << endl;
    cout << "插入排序\t\tO(n^2)\t\t\tO(1)\t\t稳定" << endl;
    cout << "希尔排序\t\tO(n log n)\t\tO(1)\t\t不稳定" << endl;
    cout << "归并排序\t\tO(n log n)\t\tO(n)\t\t稳定" << endl;
    cout << "快速排序\t\tO(n log n)\t\tO(log n)\t不稳定" << endl;
    cout << "堆排序\t\t\tO(n log n)\t\tO(1)\t\t不稳定" << endl;
    cout << "计数排序\t\tO(n + k)\t\tO(k)\t\t稳定" << endl;
    cout << "基数排序\t\tO(d*(n+k))\t\tO(n+k)\t\t稳定" << endl;
    cout << "桶排序\t\t\tO(n + k)\t\tO(n+k)\t\t稳定" << endl;
    cout << "-----------------------------------------------------------" << endl;
    
    return 0;
}
