using UnityEngine;

public class HandRotator : MonoBehaviour
{
    public SerialController serialController;

    // Index finger
    public Transform index1;
    public Transform index2;
    public float indexOffsetY1 = 160;
    public float indexOffsetZ1 = 180;
    public float indexOffset2 = 180;
    public int indexNY = 4; // The nth value in the array for rotating index1 on Y axis
    public int indexNZ = 5; // The nth value in the array for rotating index1 on Z axis
    public int indexM = 6; // The mth value in the array for rotating index2
    public float indexRotationScaleY1 = 1.0f; // Scale the rotation amount for index1 on Y axis
    public float indexRotationScaleZ1 = 1.0f; // Scale the rotation amount for index1 on Z axis
    public float indexRotationScale2 = -0.5f; // Scale the rotation amount for index2

    // Middle finger
    public Transform middle1;
    public Transform middle2;
    public float middleOffsetY1 = 0;
    public float middleOffsetZ1 = 180;
    public float middleOffset2 = 60;
    public int middleNY = 7; // The nth value in the array for rotating middle1 on Y axis
    public int middleNZ = 8; // The nth value in the array for rotating middle1 on Z axis
    public int middleM = 9; // The mth value in the array for rotating middle2
    public float middleRotationScaleY1 = 1f; // Scale the rotation amount for middle1 on Y axis
    public float middleRotationScaleZ1 = 1.0f; // Scale the rotation amount for middle1 on Z axis
    public float middleRotationScale2 = -2f; // Scale the rotation amount for middle2

    // Ring finger
    public Transform ring1;
    public Transform ring2;
    public float ringOffsetY1 = 270;
    public float ringOffsetZ1 = 180;
    public float ringOffset2 = 180;
    public int ringNY = 10; // The nth value in the array for rotating ring1 on Y axis
    public int ringNZ = 11; // The nth value in the array for rotating ring1 on Z axis
    public int ringM = 12; // The mth value in the array for rotating ring2
    public float ringRotationScaleY1 = 0.5f; // Scale the rotation amount for ring1 on Y axis
    public float ringRotationScaleZ1 = 1.0f; // Scale the rotation amount for ring1 on Z axis
    public float ringRotationScale2 = -0.5f; // Scale the rotation amount for ring2

    // Pinky finger
    public Transform pinky1;
    public Transform pinky2;
    public float pinkyOffsetY1 = 0;
    public float pinkyOffsetZ1 = 250;
    public float pinkyOffset2 = 150;
    public int pinkyNY = 13; // The nth value in the array for rotating pinky1 on Y axis
    public int pinkyNZ = 14; // The nth value in the array for rotating pinky1 on Z axis
    public int pinkyM = 15; // The mth value in the array for rotating pinky2
    public float pinkyRotationScaleY1 = 0f; // Scale the rotation amount for pinky1 on Y axis
    public float pinkyRotationScaleZ1 = -1f; // Scale the rotation amount for pinky1 on Z axis
    public float pinkyRotationScale2 = -0.5f; // Scale the rotation amount for pinky2

    // Thumb
    public Transform thumb1;
    public Transform thumb2;
    public float thumbOffsetY1 = 90;
    public float thumbOffsetZ1 = 250;
    public float thumbOffset2 = 0;
    public int thumbNY = 0; // The nth value in the array for rotating thumb1 on Y axis
    public int thumbNZ = 1; // The nth value in the array for rotating thumb1 on Z axis
    public int thumbM = 3; // The mth value in the array for rotating thumb2
    public float thumbRotationScaleY1 = 0.1f; // Scale the rotation amount for thumb1 on Y axis
    public float thumbRotationScaleZ1 = 0.5f; // Scale the rotation amount for thumb1 on Z axis
    public float thumbRotationScale2 = 3f; // Scale the rotation amount for thumb2

    private Quaternion originalRotationIndex1;
    private Quaternion originalRotationIndex2;
    private Quaternion originalRotationMiddle1;
    private Quaternion originalRotationMiddle2;
    private Quaternion originalRotationRing1;
    private Quaternion originalRotationRing2;
    private Quaternion originalRotationPinky1;
    private Quaternion originalRotationPinky2;
    private Quaternion originalRotationThumb1;
    private Quaternion originalRotationThumb2;

    private const int stackSize = 30;
    private float[] indexStackY1 = new float[stackSize];
    private float[] indexStackZ1 = new float[stackSize];
    private float[] indexStack2 = new float[stackSize];
    private float[] middleStackY1 = new float[stackSize];
    private float[] middleStackZ1 = new float[stackSize];
    private float[] middleStack2 = new float[stackSize];
    private float[] ringStackY1 = new float[stackSize];
    private float[] ringStackZ1 = new float[stackSize];
    private float[] ringStack2 = new float[stackSize];
    private float[] pinkyStackY1 = new float[stackSize];
    private float[] pinkyStackZ1 = new float[stackSize];
    private float[] pinkyStack2 = new float[stackSize];
    private float[] thumbStackY1 = new float[stackSize];
    private float[] thumbStackZ1 = new float[stackSize];
    private float[] thumbStack2 = new float[stackSize];

    private int currentIndex = 0;

    void Start()
    {
        // Initialize stacks
        for (int i = 0; i < stackSize; i++)
        {
            indexStackY1[i] = 1f;
            indexStackZ1[i] = 1f;
            indexStack2[i] = 1f;
            middleStackY1[i] = 1f;
            middleStackZ1[i] = 1f;
            middleStack2[i] = 1f;
            ringStackY1[i] = 1f;
            ringStackZ1[i] = 1f;
            ringStack2[i] = 1f;
            pinkyStackY1[i] = 1f;
            pinkyStackZ1[i] = 1f;
            pinkyStack2[i] = 1f;
            thumbStackY1[i] = 1f;
            thumbStackZ1[i] = 1f;
            thumbStack2[i] = 1f;
        }

        // Store the original rotations for each finger and thumb
        if (index1 != null)
            originalRotationIndex1 = index1.localRotation;
        if (index2 != null)
            originalRotationIndex2 = index2.localRotation;
        if (middle1 != null)
            originalRotationMiddle1 = middle1.localRotation;
        if (middle2 != null)
            originalRotationMiddle2 = middle2.localRotation;
        if (ring1 != null)
            originalRotationRing1 = ring1.localRotation;
        if (ring2 != null)
            originalRotationRing2 = ring2.localRotation;
        if (pinky1 != null)
            originalRotationPinky1 = pinky1.localRotation;
        if (pinky2 != null)
            originalRotationPinky2 = pinky2.localRotation;
        if (thumb1 != null)
            originalRotationThumb1 = thumb1.localRotation;
        if (thumb2 != null)
            originalRotationThumb2 = thumb2.localRotation;
    }

    void Update()
    {
        if (serialController != null && serialController.sensorValues.Length > Mathf.Max(indexNY, indexNZ, indexM, middleNY, middleNZ, middleM, ringNY, ringNZ, ringM, pinkyNY, pinkyNZ, pinkyM, thumbNY, thumbNZ, thumbM))
        {
            RotateFingers();
        }
    }

    void RotateFingers()
    {
        // Rotate index finger
        if (index1 != null)
        {
            UpdateStack(indexStackY1, serialController.sensorValues[indexNY] * indexRotationScaleY1 - indexOffsetY1);
            UpdateStack(indexStackZ1, serialController.sensorValues[indexNZ] * indexRotationScaleZ1 - indexOffsetZ1);
            index1.localRotation = originalRotationIndex1 * Quaternion.Euler(0, AverageStack(indexStackY1), AverageStack(indexStackZ1));
        }
        if (index2 != null)
        {
            UpdateStack(indexStack2, serialController.sensorValues[indexM] * indexRotationScale2 - indexOffset2);
            index2.localRotation = originalRotationIndex2 * Quaternion.Euler(0, 0, AverageStack(indexStack2));
        }

        // Rotate middle finger
        if (middle1 != null)
        {
            UpdateStack(middleStackY1, serialController.sensorValues[middleNY] * middleRotationScaleY1 - middleOffsetY1);
            UpdateStack(middleStackZ1, serialController.sensorValues[middleNZ] * middleRotationScaleZ1 - middleOffsetZ1);
            middle1.localRotation = originalRotationMiddle1 * Quaternion.Euler(0, AverageStack(middleStackY1), AverageStack(middleStackZ1));
        }
        if (middle2 != null)
        {
            //only enable if middle's sensor value is above 500
            if (serialController.sensorValues[middleM] > 500)
            {
                UpdateStack(middleStack2, serialController.sensorValues[middleM] * middleRotationScale2 - middleOffset2);
                middle2.localRotation = originalRotationMiddle2 * Quaternion.Euler(0, 0, AverageStack(middleStack2));
            }
        }

        // Rotate ring finger
        if (ring1 != null)
        {
            UpdateStack(ringStackY1, serialController.sensorValues[ringNY] * ringRotationScaleY1 - ringOffsetY1);
            UpdateStack(ringStackZ1, serialController.sensorValues[ringNZ] * ringRotationScaleZ1 - ringOffsetZ1);
            ring1.localRotation = originalRotationRing1 * Quaternion.Euler(0, AverageStack(ringStackY1), AverageStack(ringStackZ1));
        }
        if (ring2 != null)
        {
            UpdateStack(ringStack2, serialController.sensorValues[ringM] * ringRotationScale2 - ringOffset2);
            ring2.localRotation = originalRotationRing2 * Quaternion.Euler(0, 0, AverageStack(ringStack2));
        }

        // Rotate pinky finger
        if (pinky1 != null)
        {
            UpdateStack(pinkyStackY1, serialController.sensorValues[pinkyNY] * pinkyRotationScaleY1 - pinkyOffsetY1);
            UpdateStack(pinkyStackZ1, serialController.sensorValues[pinkyNZ] * pinkyRotationScaleZ1 - pinkyOffsetZ1);
            pinky1.localRotation = originalRotationPinky1 * Quaternion.Euler(0, AverageStack(pinkyStackY1), AverageStack(pinkyStackZ1));
        }
        if (pinky2 != null)
        {
            UpdateStack(pinkyStack2, serialController.sensorValues[pinkyM] * pinkyRotationScale2 - pinkyOffset2);
            pinky2.localRotation = originalRotationPinky2 * Quaternion.Euler(0, 0, AverageStack(pinkyStack2));
        }

        // Rotate thumb
        //same condition as middle finger
        if (thumb1 != null)
        {
            UpdateStack(thumbStackY1, serialController.sensorValues[thumbNY] * thumbRotationScaleY1 - thumbOffsetY1);
            UpdateStack(thumbStackZ1, serialController.sensorValues[thumbNZ] * thumbRotationScaleZ1 - thumbOffsetZ1);
            thumb1.localRotation = originalRotationThumb1 * Quaternion.Euler(0, AverageStack(thumbStackY1), AverageStack(thumbStackZ1));
        }
        if (thumb2 != null)
        {
            UpdateStack(thumbStack2, serialController.sensorValues[thumbM] * thumbRotationScale2 - thumbOffset2);
            thumb2.localRotation = originalRotationThumb2 * Quaternion.Euler(0, 0, AverageStack(thumbStack2));
        }

        // Increment the current index for stack updates
        currentIndex = (currentIndex + 1) % stackSize;
    }

    void UpdateStack(float[] stack, float newValue)
    {
        stack[currentIndex] = newValue;
    }

    float AverageStack(float[] stack)
    {
        float sum = 0;
        for (int i = 0; i < stackSize; i++)
        {
            sum += stack[i];
        }
        return sum / stackSize;
    }
}
