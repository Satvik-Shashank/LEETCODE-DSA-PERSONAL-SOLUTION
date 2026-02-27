# 1480. Running Sum of 1d Array

**Difficulty:** Easy

---

## Problem Summary

Given an array nums. We define a running sum of an array as runningSum[i] = sum(nums[0]…nums[i]).

Return the running sum of nums.

 
Example 1:

Input: nums = [1,2,3,4]
Output: [1,3,6,10]
Explanation: Running sum is obtained as follows: [1, 1+2, 1+2+3, 1+2+3+4].

Example 2:

Input: nums = [1,1,1,1,1]
Output: [1,2,3,4,5]
Explanation: Running sum is obtained as follows: [1, 1+1, 1+1+1, 1+1+1+1, 1+1+1+1+1].

Example 3:

Input: nums = [3,1,2,10,1]
Output: [3,4,6,16,17]

 
Constraints:

	1 <= ...

---

## Approach

### Most Efficient Approach

**Pattern: Prefix Sum**

1. Build a prefix sum array where prefix[i] = sum of elements from index 0 to i.
2. Any subarray sum from index i to j can be computed as prefix[j] - prefix[i-1].
3. Use this property to answer range-sum queries in O(1) time.
4. For cumulative results, iterate once and accumulate running totals.

### My Approach

1. Iterate through the input (1 loop).
2. Build the result by appending/accumulating values.
3. Return the final result.

---

## Complexity Analysis

| Metric | Value |
|--------|-------|
| Time   | O(n) |
| Space  | O(1) |

Single pass through the input. No significant extra space is used.

---

## Code

```py
class Solution:
    def runningSum(self, nums: List[int]) -> List[int]:
        for i in range(1, len(nums)):
            nums[i] += nums[i - 1]
        return nums
        

    
```
