#!/usr/bin/env python3


mux = 2
nslices = 60
tr = 5.0
mux_slice_acq_order = list(range(0,nslices,2)) + list(range(1,nslices,2))
mux_slice_acq_time = [float(s)/nslices*tr for s in range(nslices)]
unmux_slice_acq_order = [nslices*m+s for m in range(mux) for s in mux_slice_acq_order]
slice_time = {slice_num:slice_time for slice_num,slice_time in zip(unmux_slice_acq_order, mux_slice_acq_time*3)}
for slice,acq in sorted(slice_time.items(), key=slice_time):
    print(f'slice {slice} acquired at time {acq} sec')
