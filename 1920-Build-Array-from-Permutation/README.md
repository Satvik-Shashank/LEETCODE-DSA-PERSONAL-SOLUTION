# 1920. Build Array from Permutation

**Difficulty:** Easy

---

## Problem Summary

Given a zero-based permutation nums (0-indexed), build an array ans of the same length where ans[i] = nums[nums[i]] for each 0 <= i < nums.length and return it.

A zero-based permutation nums is an array of distinct integers from 0 to nums.length - 1 (inclusive).

 
Example 1:

Input: nums = [0,2,1,5,3,4]
Output: [0,1,2,4,5,3]
Explanation: The array ans is built as follows: 
ans = [nums[nums[0]], nums[nums[1]], nums[nums[2]], nums[nums[3]], nums[nums[4]], nums[nums[5]]]
    = [nums[0], nums[2], ...

---

## Approach

### Most Efficient Approach

**Pattern: Array In-place**

1. Use the array indices themselves to encode information (e.g., mark visited elements).
2. Iterate through the array, placing each element at its correct position.
3. Use modular arithmetic or sign flipping to store extra data without extra space.
4. Extract the final result from the modified array.

### My Approach

1. Return the final result.

---

## Complexity Analysis

| Metric | Value |
|--------|-------|
| Time   | O(1) |
| Space  | O(1) |

Constant-time operations with no loops. No significant extra space is used.

---

## Code

```py
class Solution:
    def buildArray(self, nums: List[int]) -> List[int]:
        return [nums[x] for x in nums]
        
```
