## Cost Computation Notes

The `cost_estimator` only tracks instance costs. While this is definitely easier for the coders, we, the coders, would also like to justify our sloth verbally:


- Our expectation is that storage and networking costs will be the only significant cost, apart from instance/GPU costs.

- Let's look at Google Cloud costs for executing a 1,000,000 image run:

- To run predictions on 1,000,000 1.5Mb images, we need

  1. 1.5Tb in bucket storage: ($0.026/Gb/month) = $39/month, which comes out to ~$1.50 for an current standard run length of just over one day.
  2. network bandwidth to upload to the bucket, which turns out to be free
  3. to read from the bucket, which will be, in the worst case* where we have a bucket in one region in North America (e.g., us-west1) and have the cluster in another North American region (e.g., us-west2), $0.01/Gb, which means we’d spend ~$10 on data transfer.
  4. to carry out three Google Cloud operations per image file: upload, make public, download. For a 1,000,000 image run, that is 3,000,000 operations. The downloading operations are “Class B operations” and are billed at $0.004/10,000 operations. The publication operations are “Class A operations” and are billed at $0.05/10,000 operations. The uploading operations are, apparently, free. So, for a 1,000,000 image run, we would incur $0.40 for download fees and $5.00 for publication fees.

- So, in the worst case*, we can expect to spend ~$17.00 in non-instance/GPU fees for a 1,000,000 image run. In the best case, it’d be more like ~$7.00.

<br></br>

<b>*caveats:</b>

1. The "worst case*" is the worst case for the Van Valen Lab. Critically, we are assuming that users will not accidentally put their storage bucket and GKE cluster on different continents. Doing so exposes them to massive data transfer fees (currently, anywhere from ~$180 to ~$345 for our 1,000,000 image run).
2. We’re also assuming that users will delete the 1,000,000 images in their buckets after the run finishes. If they don’t they could start racking up a serious bill. (~$1.25/day can add up after a while, especially if you end up doing multiple 1,000,000 image runs.)
