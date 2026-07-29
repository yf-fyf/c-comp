let read_file path =
  let ic = open_in_bin path in
  let len = in_channel_length ic in
  let data = really_input_string ic len in
  close_in ic;
  data
